# /// script
# requires-python = ">=3.11"
# dependencies = ["arkitekt[rekuest]>=5", "koil>=3.3.4", "numpy>=1.26"]
# ///
"""Stateful: a simulated microscope stage others can watch and drive.

Run:  uv run --script examples/microscope_stage.py

``@app.state`` declares a class whose instances the platform publishes — the UI
shows the live position without polling an action for it. ``@app.startup``
builds it once when the app starts providing, ``@app.background`` keeps it
moving, and every action annotated with the class is handed the same instance.

Swap the sleeps for your stage's serial calls and this is a real device app.
"""

from typing import Annotated

import koil
import numpy as np

from arkitekt import App, Description, Task, run

app = App("microscope-stage", "0.1.0")


@app.state
class StagePosition:
    """Where the stage is, in micrometers, and whether it is settled."""

    x_um: float = 0.0
    y_um: float = 0.0
    z_um: float = 0.0
    moving: bool = False


@app.startup
def home_the_stage() -> StagePosition:
    """Home the stage when the app starts providing."""
    print("Homing stage...")
    return StagePosition()


@app.action
def move_to(
    state: StagePosition,
    x_um: Annotated[float, Description("Target x, in micrometers")],
    y_um: Annotated[float, Description("Target y, in micrometers")],
    z_um: Annotated[float, Description("Target z, in micrometers")] = 0.0,
    *,
    task: Task,
) -> float:
    """Move To

    Drives the stage there in 20 steps and returns the distance travelled.
    """
    start = np.array([state.x_um, state.y_um, state.z_um])
    target = np.array([x_um, y_um, z_um])
    state.moving = True
    for step in range(1, 21):
        state.x_um, state.y_um, state.z_um = start + (target - start) * step / 20
        task.progress(step * 5, f"At {state.x_um:.1f}, {state.y_um:.1f}")
        koil.sleep(0.05)
    state.moving = False
    return float(np.linalg.norm(target - start))


@app.background
def report_drift(state: StagePosition) -> None:
    """Add the thermal drift a real stage would have, once a second."""
    rng = np.random.default_rng(0)
    while True:
        if not state.moving:
            state.x_um += float(rng.normal(0, 0.01))
            state.y_um += float(rng.normal(0, 0.01))
        koil.sleep(1)


if __name__ == "__main__":
    run(app)
