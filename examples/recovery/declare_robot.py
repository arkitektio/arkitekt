# /// script
# requires-python = ">=3.11"
# dependencies = ["arkitekt>=3", "koil>=3.3.4"]
# ///
"""A robot, whose actions can't be taken back.

Run:  uv run --script examples/recovery/declare_robot.py

``effects=`` says what running an action again would do to the world:

    NONE < REPEATABLE < UNKNOWN (no claim) < IRREVERSIBLE

On an app it is the default for actions that make no claim of their own; an action's
own claim is more specific, and wins. The claim is *information*, not a rule: a
workflow reads it off ``AgentLost.effects``, a person sees it on a hold or in the UI.

``@app.state`` publishes what the robot knows about the world. A workflow can *guard*
on it: if the plate state changed while the workflow was down, it learns so instead
of carrying on blind. A guard sees only what is modelled here, so the robot says
which plate is loaded and what has been put in which well.
"""

from dataclasses import field

import koil

from arkitekt import App, Effects, Task, run

app = App("liquid-handler", "0.1.0", effects=Effects.IRREVERSIBLE)


@app.state
class Plate:
    """The plate on the deck, and what has gone into it."""

    barcode: str = ""
    dispensed_ul: dict[str, float] = field(default_factory=dict)


@app.startup
def no_plate() -> Plate:
    """Start with an empty deck."""
    return Plate()


@app.action
def load_plate(plate: Plate, barcode: str) -> str:
    """Load Plate

    Records a new plate on the deck. Any guard on the old plate now fails.
    """
    plate.barcode = barcode
    plate.dispensed_ul = {}
    return barcode


@app.action
def dispense(plate: Plate, well: str, volume_ul: float, *, task: Task) -> float:
    """Dispense

    Moves liquid into a well. Running it again puts twice the volume in the well.
    """
    for step in range(10):
        task.progress((step + 1) * 10, f"Dispensing into {well}")
        koil.sleep(0.2)
    plate.dispensed_ul = {**plate.dispensed_ul, well: plate.dispensed_ul.get(well, 0) + volume_ul}
    return volume_ul


@app.action(effects=Effects.NONE)
def read_absorbance(well: str) -> float:
    """Read Absorbance

    Reads the plate reader. Moves nothing, so it overrides the app's default.
    """
    return 0.42


if __name__ == "__main__":
    run(app)
