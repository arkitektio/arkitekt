"""``connect(Mikro)``: a script's clients, connected.

```python
from arkitekt import connect
from mikro import Mikro

with connect(Mikro) as mikro:                       # the client
    mikro.get_array_dataset(12)

with connect(Mikro, Fluss) as (mikro, fluss): ...   # several: a tuple, in order
async with connect(Mikro) as mikro: ...
mikro = connect(Mikro).enter()                      # a notebook: stays connected
```

It is ``App(<the calling file's name>, clients=[...])`` connected: the app logs in
under that identifier (``identifier=`` names another). An app that offers actions is
declared with :class:`~arkitekt.App` and given to ``connect(app)`` or ``run(app)``.
"""

import atexit
from types import TracebackType
from typing import Any, Generic, TypeVar, cast

from koil import Koil

from arkitekt.app.app import App, _app_namespace, _app_root
from arkitekt.runtime import Runtime

R = TypeVar("R")


class Connected(Generic[R]):
    """A script's app and how to connect it. Enter it for the clients.

    Each ``with``/``async with`` enters a fresh runtime, so it can be entered again.

    Attributes:
        app: The app declared for the script.
        clients: The client classes handed back, in order.
    """

    def __init__(
        self, app: App[Any], clients: tuple[type, ...], options: dict[str, Any]
    ) -> None:
        self.app = app
        self.clients = clients
        self._options = options
        self._runtimes: list[Runtime[Any]] = []

    def __repr__(self) -> str:
        names = ", ".join(cls.__name__ for cls in self.clients)
        return f"Connected({self.app.identifier!r}, {names})"

    def runtime(self) -> Runtime[Any]:
        """A fresh, unentered runtime of the app, connected as configured."""
        from arkitekt.runtime import connect

        return connect(self.app, **self._options)

    def resolve(self, runtime: Runtime[Any]) -> R:
        """The named clients of an entered runtime: one, or a tuple of several."""
        found = tuple(runtime.require(cls) for cls in self.clients)
        return cast(R, found[0] if len(found) == 1 else found)

    def __enter__(self) -> R:
        runtime = self.runtime()
        runtime.__enter__()
        self._runtimes.append(runtime)
        return self.resolve(runtime)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._runtimes.pop().__exit__(exc_type, exc_value, traceback)

    async def __aenter__(self) -> R:
        runtime = self.runtime()
        await runtime.__aenter__()
        self._runtimes.append(runtime)
        return self.resolve(runtime)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._runtimes.pop().__aexit__(exc_type, exc_value, traceback)

    def enter(self) -> R:
        """Connect and stay connected until the process exits: for a notebook.

        Entering again for the same app (a re-run cell) leaves the previous run first.
        """
        _leave(self.app.identifier)
        runtime = self.runtime()
        # A notebook runs its own event loop; let sync calls run inside it.
        setattr(runtime, "__koil", Koil(sync_in_async=True))
        runtime.enter()
        _entered[self.app.identifier] = runtime
        return self.resolve(runtime)


#: Runtimes :meth:`Connected.enter` keeps open, by app identifier.
_entered: dict[str, Runtime[Any]] = {}


def _leave(identifier: str | None = None) -> None:
    """Leave the run entered for ``identifier``, or every one (newest first) at exit."""
    names = [identifier] if identifier is not None else list(reversed(_entered))
    for name in names:
        runtime = _entered.pop(name, None)
        if runtime is None:
            continue
        try:
            runtime.__exit__(None, None, None)
        except Exception:  # noqa: BLE001 -- the process may be exiting anyway
            pass


atexit.register(_leave)


def connected(
    classes: tuple[type, ...],
    caller: Any,  # noqa: ANN401 -- arkitekt.app.app._caller's result
    *,
    identifier: str | None,
    version: str,
    logo: str | None,
    scopes: list[str] | None,
    author: str | None,
    options: dict[str, Any],
) -> Connected[Any]:
    """The script app using ``classes``, constructed for ``caller``'s file.

    Raises:
        TypeError: If a class is not a ``@client``.
    """
    constructed_in = caller[0]
    app = App(
        identifier or constructed_in.stem,
        version,
        logo=logo,
        scopes=scopes,
        author=author,
        clients=list(classes),
        root=_app_root(constructed_in),
    )
    # The caller's source is the app's own, not this module's.
    app.namespace = _app_namespace(app.identifier, caller)
    return Connected(app, classes, options)


__all__ = ["Connected"]
