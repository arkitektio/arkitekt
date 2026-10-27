"""Importing an app without letting it reach a server: what ``arkitekt check`` loads it under.

An app module should only declare. One that runs or connects when it is imported (a
``run(app)`` or a ``with connect(app)`` at module level, not behind
``if __name__ == "__main__":``) would otherwise log in and talk to a server while it is
only being checked. Under :func:`offline`:

- ``run`` and ``arun`` return at once: the app they were handed is what is checked;
- entering a runtime (``with connect(app)``, ``easy(...)``, what ``run`` does), logging in
  (``alogin``) and starting a detached run raise :class:`ConnectedAtImport`, which the
  check reports at the module's line.
"""

from collections.abc import Generator
from contextlib import contextmanager, ExitStack
from types import ModuleType

import arkitekt
import arkitekt.runtime as runtime_module
from arkitekt.runtime import Runtime


class ConnectedAtImport(RuntimeError):
    """An app module tried to reach a server while it was imported to be checked."""


_ADVICE = "move it behind `if __name__ == \"__main__\":` so that importing the app only declares it"


def _refuse(what: str) -> ConnectedAtImport:
    return ConnectedAtImport(f"The app {what} while it is imported: {_ADVICE}.")


def _skip_run(*args: object, **kwargs: object) -> None:
    """``run(app)`` under a check: the app is declared, nothing is run."""
    del args, kwargs


async def _skip_arun(*args: object, **kwargs: object) -> None:
    """``await arun(app)`` under a check: the app is declared, nothing is run."""
    del args, kwargs


def _refuse_detached(*args: object, **kwargs: object) -> None:
    del args, kwargs
    raise _refuse("starts a detached run")


async def _refuse_login(*args: object, **kwargs: object) -> None:
    del args, kwargs
    raise _refuse("logs in")


def _refuse_enter(self: Runtime[object]) -> Runtime[object]:
    del self
    raise _refuse("connects (it enters a runtime)")


async def _refuse_aenter(self: Runtime[object]) -> Runtime[object]:
    del self
    raise _refuse("connects (it enters a runtime)")


def _patch(stack: ExitStack, owner: ModuleType | type, name: str, value: object) -> None:
    """Set ``owner.name`` for the stack's lifetime; a class attribute it only inherited is
    removed again rather than copied onto it."""
    if isinstance(owner, type) and name not in owner.__dict__:
        setattr(owner, name, value)
        _ = stack.callback(delattr, owner, name)
        return
    original: object = vars(owner)[name]  # pyright: ignore[reportAny] -- whatever was there goes back
    setattr(owner, name, value)
    _ = stack.callback(setattr, owner, name, original)


@contextmanager
def offline() -> Generator[None]:
    """Stub out every way an app module reaches a server, for as long as it is imported."""
    with ExitStack() as stack:
        for owner in (arkitekt, runtime_module):
            _patch(stack, owner, "run", _skip_run)
            _patch(stack, owner, "arun", _skip_arun)
            _patch(stack, owner, "run_detached", _refuse_detached)
        _patch(stack, runtime_module, "alogin", _refuse_login)
        _patch(stack, Runtime, "__enter__", _refuse_enter)
        _patch(stack, Runtime, "__aenter__", _refuse_aenter)
        yield
