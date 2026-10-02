# /// script
# requires-python = ">=3.11"
# dependencies = ["arkitekt[rekuest,mikro]>=5"]
# ///
"""A workflow that survives its own crash and its steps'.

Run:  uv run --script examples/recovery/workflow.py

``@app.workflow`` is a different kind of action, not an effect level. Two things can
go wrong, and each has one answer:

**The workflow's own agent dies. The platform resumes it.** The code runs again from
the top, but every call that already finished returns its recorded result instead of
running, and ``task.now()`` returns the recorded time. So workflow code must be
deterministic: outside values come in only through ``task`` and through calls.
Finished work is never redone, whatever its effects.

**A step's agent dies. The workflow's code handles it.** The call raises
``AgentLost``, and the exception says what is known:

- ``started``: whether the step was ever picked up (if not, retrying is always safe);
- ``last_progress``: what it last reported;
- ``effects``: what running it again would do (information, never a rule).

The workflow decides with the context only it has. ``task.retry(...)`` retries on its
own only a step that never started; ``if_started=True`` is you saying a repeat is fine.
``task.hold(...)`` parks the workflow for a person, with what is known in front of them.

**Guards: the world may change while the workflow is down.** ``with
task.guard(handler.plate, "barcode"):`` records the revision of the robot's plate
state. On resume, if something other than this workflow's own calls changed the
barcode in between (someone loaded another plate), or the robot restarted, the block
raises ``StateChanged`` instead of dispensing into the wrong plate. This is optimistic,
like HTTP's ``If-Match``: nothing is locked while the workflow is down; the change is
noticed when it comes back.
"""

from typing import Protocol

from mikro import mikro_service
from mikro.arkitekt.specs import LabelMask, SingleChannelImage

from arkitekt import AgentLost, App, StateChanged, Task, run

app = App("plate-workflow", "0.1.0", services=[mikro_service])


class PlateState(Protocol):
    """What the workflow reads of the robot's plate: the fields its ``plate`` state must have."""

    barcode: str
    dispensed_ul: dict[str, float]


@app.declare(app="segmentation", auto_resolvable=True, min=1)
class Segmentation(Protocol):
    """What this workflow needs from the segmentation app."""

    def count_cells(self, image: SingleChannelImage) -> int:
        """Count Cells"""
        ...

    def segment(self, image: SingleChannelImage) -> LabelMask:
        """Segment"""
        ...


@app.declare(app="liquid-handler", auto_resolvable=True, min=1)
class LiquidHandler(Protocol):
    """What this workflow needs from the liquid handler."""

    plate: PlateState

    def dispense(self, well: str, volume_ul: float) -> float:
        """Dispense"""
        ...

    def read_absorbance(self, well: str) -> float:
        """Read Absorbance"""
        ...


@app.workflow
def stain_and_measure(
    segmentation: Segmentation,
    handler: LiquidHandler,
    image: SingleChannelImage,
    well: str,
    *,
    task: Task,
) -> float:
    """Stain And Measure

    Counts the cells in the well's image, doses dye in proportion, then reads the well.
    """
    started = task.now()  # recorded: a resumed run sees the same start time

    # count_cells changes nothing: if its agent dies, just try again, even after it
    # started. task.retry retries only on AgentLost, and only a started step when told.
    cells = task.retry(segmentation.count_cells, image, attempts=3, if_started=True)

    # segment stores a dataset and makes no claim. If its agent dies after it
    # started, a retry might leave a duplicate. This workflow keeps the labels only
    # for the record, so it goes on without them rather than guess.
    try:
        segmentation.segment(image)
    except AgentLost as lost:
        task.log(f"segmentation lost ({lost.last_progress}%), continuing without labels")

    volume = 0.5 * cells
    try:
        with task.guard(handler.plate, "barcode"):
            try:
                handler.dispense(well, volume_ul=volume)
            except AgentLost as lost:
                if not lost.started:
                    # Never reached the robot: nothing was dispensed.
                    handler.dispense(well, volume_ul=volume)
                else:
                    # Started, irreversible, fate unknown. A person checks the well,
                    # then resumes (the dispense counts as done) or abandons.
                    task.hold(
                        f"Dispense of {volume} µl into {well} was lost: "
                        "check the well, then resume or abandon.",
                        lost=lost,  # its effects and last progress, in front of the person
                    )
            absorbance = task.retry(handler.read_absorbance, well, attempts=3, if_started=True)
    except StateChanged as changed:
        # The plate was swapped while this workflow was down: whatever comes next
        # would land in the wrong plate.
        raise RuntimeError(f"Not continuing: {changed}") from None

    task.log(f"{cells} cells, {absorbance:.3f} OD, {task.now() - started:.1f}s")
    return absorbance


if __name__ == "__main__":
    run(app)
