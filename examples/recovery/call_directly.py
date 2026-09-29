# /// script
# requires-python = ">=3.11"
# dependencies = ["arkitekt[mikro]>=3"]
# ///
"""Calling from a script: a lost task is yours to decide about.

Run:  uv run --script examples/recovery/call_directly.py

If the agent running a task dies, the server re-runs nothing: the task ends LOST, and
``call`` raises ``AgentLost`` with what is known (was it ever started, how far did it
get, what would running it again do). A script decides like a workflow does, in code.
The same ``retry`` a workflow's task has is there for the common case.

The action and dataset ids come from the UI ("Copy id") to keep this short.
"""

from mikro import mikro_service
from rekuest.arkitekt import rekuest_service

from arkitekt import AgentLost, easy, retry

COUNT = "segmentation/count_cells"
DISPENSE = "liquid-handler/dispense"

IMAGE_DATASET = "1234"  # an image already in mikro


def main() -> None:
    """Count the cells, then dose: retry the one, ask a person about the other."""
    with easy("plate-runner", rekuest_service, mikro_service) as (rekuest, mikro):
        image = mikro.get_array_dataset(IMAGE_DATASET).lens()

        # Counting changes nothing: if its agent dies, try again, even after it started.
        cells = retry(rekuest.call, COUNT, image=image, attempts=3, if_started=True)

        try:
            rekuest.call(DISPENSE, well="A1", volume_ul=0.5 * cells)
        except AgentLost as lost:
            if not lost.started:
                # It never reached the robot: nothing was dispensed, sending it again is safe.
                rekuest.call(DISPENSE, well="A1", volume_ul=0.5 * cells)
            else:
                # Started, and running it again would happen again in the real world.
                print(
                    f"The dispense into A1 was lost at {lost.last_progress}% "
                    f"(effects: {lost.effects}). Check the well before doing anything else."
                )


if __name__ == "__main__":
    main()
