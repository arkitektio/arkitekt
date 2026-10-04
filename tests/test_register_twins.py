"""Every ``@app.<x>`` has a plain call beside it: ``app.register_<x>(target, ...)``.

A decorator suits what is declared where it is written. What is declared under a
condition, or written somewhere else -- a host offering only the actions its
hardware has -- is registered by a call, and declares exactly the same thing.
"""

from typing import Protocol

import pytest
from arkitekt_spec.declare.structures.errors import StructureDefinitionError

from arkitekt import App, Effects

from .fakes import RekuestProvider


def _app(identifier: str = "twins") -> App[None]:
    return App(identifier, providers=[RekuestProvider()])


def move(x: int) -> int:
    """Moves the stage."""
    return x


def test_an_action_registered_by_call_is_the_action_the_decorator_declares() -> None:
    decorated, called = _app(), _app()
    decorated.action(effects=Effects.IRREVERSIBLE, locks=["stage"])(move)
    wrapped = called.register_action(move, effects=Effects.IRREVERSIBLE, locks=["stage"])

    assert wrapped(3) == 3, "still callable as itself"
    ours, theirs = (
        app.registry.implementations["move"] for app in (called, decorated)
    )
    assert ours.definition == theirs.definition
    assert (ours.effects, ours.locks) == (theirs.effects, theirs.locks)


def test_a_workflow_registered_by_call_is_a_workflow() -> None:
    app = _app()
    app.register_workflow(move)
    decorated = _app()
    decorated.workflow(move)

    assert (
        app.registry.implementations["move"].execution
        == decorated.registry.implementations["move"].execution
    )


def test_state_startup_and_background_are_registered_by_call() -> None:
    app = _app()

    class Stage:
        x: float = 0.0

    def home() -> Stage:
        return Stage()

    def follow(stage: Stage) -> None:
        return None

    def park(stage: Stage) -> None:
        return None

    assert app.register_state(Stage, name="stage") is Stage
    assert app.register_startup(home) is home
    assert app.register_background(follow) is follow
    assert app.register_shutdown(park) is park

    assert "stage" in app.registry.states
    assert Stage(x=1.0).x == 1.0, "made a dataclass, as the decorator does"
    app.snapshot()  # the declaration validates: the state has its startup hook


def test_a_context_and_a_protocol_are_registered_by_call() -> None:
    app = _app()

    class Driver:
        pass

    class Camera(Protocol):
        async def snap(self, exposure_ms: float) -> int: ...

    assert app.register_context(Driver, name="driver") is Driver
    assert app.registry.structure_registry.is_context(Driver)
    assert app.register_protocol(Camera, "lab") is Camera


def test_a_model_travels_as_its_apps_own_by_default() -> None:
    """The server only takes ``@package/key``; the app's identifier names the package."""
    app = _app("stage control")

    @app.model
    class StagePosition:
        x: float

    class Limits:
        low: float

    app.register_model(Limits)
    declared = app.registry.structure_registry
    assert declared.model_for(StagePosition).identifier == "@stage-control/stage_position"  # pyright: ignore[reportOptionalMemberAccess]
    assert declared.model_for(Limits).identifier == "@stage-control/limits"  # pyright: ignore[reportOptionalMemberAccess]


def test_a_model_identifier_the_server_would_refuse_is_refused_where_it_is_written() -> None:
    app = _app()

    with pytest.raises(StructureDefinitionError, match="@package/key"):

        @app.model(identifier="config")
        class Config:
            n: int
