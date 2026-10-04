# /// script
# requires-python = ">=3.11"
# dependencies = ["arkitekt[rekuest]>=6"]
# ///
"""Embedding: an app beside a program that has a life of its own.

Run:  uv run --script examples/embedded_host.py

Most examples are scripts: ``run(app)`` blocks until you stop it. A program you
already have -- a control program with a window, a server, threads of its own --
cannot hand its main thread over like that, and should not wrap ``run`` in a
thread of its own either. It calls ``run_detached``, gets a run it can watch and
cancel from anywhere, and goes on with its own loop.

What this shows, in the order a host needs it:

- ``App(app_context=Instrument)``: the host's own object reaches every action by
  annotation. No globals, no closures.
- ``withStateChoices``: a dropdown of what *this* installation has (its pumps),
  known only once the program runs.
- State instead of getters: nothing here reads the instrument back. What it is
  doing is published as ``InstrumentState`` and kept in sync -- by the actions
  that change it, and by the host itself when someone changes it locally.
- ``app.register_action``: the plain-call twin of ``@app.action``, for an action
  offered only when the hardware is there.
- ``device_code_hook`` / ``connection_listener`` / ``task_listener``: the login to
  approve, where the connection stands and what remote callers do, shown in the
  host's own interface (here: ``print``).
"""

import random
import time
from dataclasses import field
from typing import Annotated

import koil

from arkitekt import (
    App,
    ConnectionState,
    Description,
    DeviceCodeChallenge,
    Effects,
    Task,
    TaskEvent,
    TaskEventKind,
    has_stored_login,
    run_detached,
)
from arkitekt.widgets import withStateChoices


class Instrument:
    """The program you already have: a few pumps it drives, by name."""

    def __init__(self, pumps: list[str], has_dispenser: bool) -> None:
        self.flows = {name: 0.0 for name in pumps}
        self.has_dispenser = has_dispenser
        # The state the app publishes, once it runs: the host writes to it too.
        self.published: "InstrumentState | None" = None

    def set_flow(self, pump: str, ml_per_min: float) -> None:
        if pump not in self.flows:
            raise ValueError(f"No pump named {pump!r}: this instrument has {', '.join(self.flows)}.")
        if not 0.0 <= ml_per_min <= 50.0:
            raise ValueError("A pump runs between 0 and 50 ml/min.")
        self.flows[pump] = ml_per_min  # here: the serial call to the real pump


app = App("embedded-host", "0.1.0", app_context=Instrument)


@app.state(name="instrument")
class InstrumentState:
    """What the instrument is doing. Watch this instead of asking for it."""

    pumps: list[str] = field(default_factory=list)
    flows: dict[str, float] = field(default_factory=dict)
    dispensing: str = ""


@app.startup
def publish(instrument: Instrument) -> InstrumentState:
    """Publish the instrument as it is when the app starts providing."""
    instrument.published = InstrumentState(
        pumps=list(instrument.flows), flows=dict(instrument.flows)
    )
    return instrument.published


Pump = Annotated[str, withStateChoices("self.instrument.pumps"), Description("One of this instrument's pumps")]


@app.action(effects=Effects.REPEATABLE, locks=["instrument"])
def set_flow(
    instrument: Instrument,
    state: InstrumentState,
    pump: Pump,
    ml_per_min: Annotated[float, Description("0 stops the pump")],
) -> None:
    """Sets how fast one pump runs."""
    instrument.set_flow(pump, ml_per_min)
    state.flows[pump] = ml_per_min


def dispense(
    instrument: Instrument,
    state: InstrumentState,
    task: Task,
    pump: Pump,
    volume_ml: Annotated[float, Description("How much to dispense")],
) -> None:
    """Runs one pump until a volume went through, then stops it."""
    rate = 10.0
    instrument.set_flow(pump, rate)
    state.flows[pump], state.dispensing = rate, pump
    try:
        steps = max(1, int(volume_ml / rate * 60 / 0.5))
        for step in range(steps):
            # Where a cancelled call stops: a sync action is only told when it asks.
            task.check_cancelled()
            koil.sleep(0.5)
            task.progress(int(100 * (step + 1) / steps), f"{pump}: {volume_ml:.1f} ml")
    finally:
        instrument.set_flow(pump, 0.0)
        state.flows[pump], state.dispensing = 0.0, ""


class Host:
    """Stands in for the host program: its own loop, and a panel that is ``print``."""

    def __init__(self, instrument: Instrument) -> None:
        self.instrument = instrument
        if instrument.has_dispenser:
            # Offered only on an instrument that can do it.
            app.register_action(dispense, effects=Effects.IRREVERSIBLE, locks=["instrument"])

    def show(self, line: str) -> None:
        print(f"[panel] {line}")

    async def on_code(self, challenge: DeviceCodeChallenge) -> None:
        self.show(f"approve at {challenge.verification_uri_complete} (code {challenge.user_code})")

    async def on_state(self, state: ConnectionState) -> None:
        self.show(f"arkitekt is {state.value}")

    async def on_task(self, event: TaskEvent) -> None:
        if event.kind is TaskEventKind.ASSIGNED:
            self.show(f"called: {event.action} {event.arguments}")
        elif event.kind in (TaskEventKind.DONE, TaskEventKind.FAILED, TaskEventKind.CANCELLED):
            self.show(f"{event.action} {event.kind.value} {event.error or ''}".rstrip())

    def operate(self) -> None:
        """The host's own loop: someone at the instrument changes a pump now and then."""
        while True:
            time.sleep(5)
            pump = random.choice(list(self.instrument.flows))
            flow = float(random.choice([0, 5, 10]))
            self.instrument.set_flow(pump, flow)
            self.show(f"operator set {pump} to {flow} ml/min")
            published = self.instrument.published
            if published is not None:
                # From the host's own thread, with no action involved: watchers see it at once.
                published.flows[pump] = flow


if __name__ == "__main__":
    host = Host(Instrument(pumps=["buffer", "dye"], has_dispenser=True))
    host.show("logged in before" if has_stored_login(app) else "needs a login")
    running = run_detached(
        app,
        context=host.instrument,
        headless=True,
        device_code_hook=host.on_code,
        connection_listener=host.on_state,
        task_listener=host.on_task,
    )
    try:
        host.operate()
    except KeyboardInterrupt:
        pass
    finally:
        running.cancel()
        if running.error is not None:
            host.show(f"the run had failed: {running.error}")
