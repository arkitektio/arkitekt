"""A hub test's calls through rekuest: the switch, and what a call through rekuest asks of it.

Against a hub this is proven in ``tests/integration/test_deployment.py``; here the
runtime and the rekuest client are stand-ins that record what they are asked.
"""

from types import SimpleNamespace
from typing import Any

import pytest
from arkitekt_runtime.types import TaskPolicy

from arkitekt import App
from arkitekt.testing import (
    THROUGH_REKUEST_ENVVAR,
    TestStack,
    call_through_rekuest,
    call_through_rekuest_requested,
)


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " True "])
def test_the_environment_asks_for_calls_through_rekuest(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(THROUGH_REKUEST_ENVVAR, value)
    assert call_through_rekuest_requested()


@pytest.mark.parametrize("value", [None, "", "0", "false", "no", "off", "rekuest"])
def test_anything_else_keeps_calls_in_process(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv(THROUGH_REKUEST_ENVVAR, raising=False)
    else:
        monkeypatch.setenv(THROUGH_REKUEST_ENVVAR, value)
    assert not call_through_rekuest_requested()


class FakeRekuest:
    """Records the implementation looked up and the call made on it."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any, tuple[Any, ...], dict[str, Any]]] = []

    def my_implementation_at(self, interface: str) -> Any:  # noqa: ANN401
        return SimpleNamespace(interface=interface)

    def call(self, target: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        self.calls.append(("call", target, args, kwargs))
        return f"{target.interface} through rekuest"


class FakeRuntime:
    """A run that provides the app: an agent declaring its actions, and a rekuest client."""

    def __init__(self, declared: dict[str, Any]) -> None:
        self.agent: Any = SimpleNamespace(
            app_registry=SimpleNamespace(declared_implementations=declared)
        )
        self.rekuest = FakeRekuest()
        self.local_calls: list[tuple[Any, tuple[Any, ...], dict[str, Any]]] = []

    def require(self, cls: type) -> Any:  # noqa: ANN401
        return self.rekuest

    def call_local(self, action: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        self.local_calls.append((action, args, kwargs))
        return "in process"


def shout(text: str) -> str:
    """The plain function, as a module that kept it from before decorating has it."""
    return text.upper()


def test_a_call_through_rekuest_is_an_auto_root_task_on_the_apps_own_implementation() -> None:
    runtime = FakeRuntime({"shout": SimpleNamespace(function=shout)})

    by_name = call_through_rekuest(runtime, "shout", "hi", loud=True)  # pyright: ignore[reportArgumentType]
    by_function = call_through_rekuest(runtime, shout, text="hi")  # pyright: ignore[reportArgumentType]

    assert (by_name, by_function) == ("shout through rekuest", "shout through rekuest")
    [(_, target, args, kwargs), (_, _, _, by_keyword)] = runtime.rekuest.calls
    assert target.interface == "shout"
    assert args == ("hi",)
    # Nobody is there to approve what the action asks for.
    assert kwargs == {"loud": True, "policy": TaskPolicy.AUTO}
    assert by_keyword == {"text": "hi", "policy": TaskPolicy.AUTO}


def test_an_unknown_action_names_the_ones_there_are() -> None:
    runtime = FakeRuntime({"shout": SimpleNamespace(function=shout)})

    with pytest.raises(KeyError, match="shout"):
        call_through_rekuest(runtime, lambda: None)  # pyright: ignore[reportArgumentType]


def test_a_run_that_does_not_provide_is_not_called_through_rekuest() -> None:
    runtime = FakeRuntime({})
    runtime.agent = None

    with pytest.raises(LookupError, match="provide=True"):
        call_through_rekuest(runtime, "shout")  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize(
    ("through_rekuest", "expected"), [(False, "in process"), (True, "shout through rekuest")]
)
def test_teststack_calls_the_way_it_was_made(through_rekuest: bool, expected: str) -> None:
    runtime = FakeRuntime({"shout": SimpleNamespace(function=shout)})
    stack = TestStack(
        hub=None,  # pyright: ignore[reportArgumentType]
        app=App("shouter", "0.1.0"),
        runtime=runtime,  # pyright: ignore[reportArgumentType]
        through_rekuest=through_rekuest,
    )

    assert stack.call("shout", text="hi") == expected
    assert bool(runtime.local_calls) is not through_rekuest
    assert bool(runtime.rekuest.calls) is through_rekuest
