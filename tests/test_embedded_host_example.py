"""``examples/embedded_host.py`` declares what it says, and its actions run as written.

The example is the pattern a host program is sent to, so it must not rot: its
declaration is validated here, and its actions are called as themselves.
"""

import runpy
from pathlib import Path
from typing import Any

import pytest

from arkitekt import Task

EXAMPLE = Path(__file__).parent.parent / "examples" / "embedded_host.py"


@pytest.fixture()
def example() -> dict[str, Any]:
    return runpy.run_path(str(EXAMPLE), run_name="embedded_host")


def test_it_declares_a_state_and_no_getter(example: dict[str, Any]) -> None:
    app, host_cls, instrument_cls = example["app"], example["Host"], example["Instrument"]
    host_cls(instrument_cls(pumps=["buffer", "dye"], has_dispenser=True))

    snapshot = app.snapshot()
    offered = set(snapshot.registry.implementations)
    assert offered == {"set_flow", "dispense"}
    assert not [name for name in offered if name.startswith("get_")]
    assert "instrument" in snapshot.registry.states


def test_the_dispenser_is_offered_only_where_there_is_one(example: dict[str, Any]) -> None:
    app, host_cls, instrument_cls = example["app"], example["Host"], example["Instrument"]
    host_cls(instrument_cls(pumps=["buffer"], has_dispenser=False))

    assert set(app.registry.implementations) == {"set_flow"}


def test_the_pump_is_chosen_from_the_published_state(example: dict[str, Any]) -> None:
    app = example["app"]
    (pump,) = [
        port for port in app.registry.implementations["set_flow"].definition.args if port.key == "pump"
    ]
    assert pump.widget is not None
    assert pump.widget.state_path == "instrument.pumps"


def test_an_action_changes_the_instrument_and_the_state_together(example: dict[str, Any]) -> None:
    instrument = example["Instrument"](pumps=["buffer", "dye"], has_dispenser=False)
    state = example["publish"](instrument)

    example["set_flow"](instrument, state, "dye", 5.0)

    assert instrument.flows["dye"] == 5.0 and state.flows["dye"] == 5.0
    with pytest.raises(ValueError, match="No pump named"):
        example["set_flow"](instrument, state, "acid", 5.0)


def test_dispensing_reports_progress_and_leaves_the_pump_stopped(
    example: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("koil.sleep", lambda seconds: None)
    instrument = example["Instrument"](pumps=["buffer"], has_dispenser=True)
    state = example["publish"](instrument)

    example["dispense"](instrument, state, Task.local(), "buffer", 0.5)

    assert instrument.flows["buffer"] == 0.0
    assert (state.flows["buffer"], state.dispensing) == (0.0, "")
