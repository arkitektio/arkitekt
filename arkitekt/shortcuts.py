"""Shortcuts for scripts: declare an app, connect it, get its clients back typed.

```python
from arkitekt import aeasy, easy, interactive
from mikro import mikro_service
from fluss import fluss_service

with easy("my-script", mikro_service, fluss_service) as (mikro, fluss):   # Mikro, Fluss
    mikro.get_file(...)

with easy("my-script", mikro_service) as mikro:            # one service: the client itself
    ...

async with aeasy("my-script", mikro_service) as mikro:
    ...

mikro, fluss = interactive("notebook", mikro_service, fluss_service)  # stays connected (Jupyter)
```

Each is ``App(identifier, services=[...])`` plus :func:`~arkitekt.connect`, and the
clients come back in the order their services were named. The app and the runtime stay
reachable: ``easy(...).app`` is the declaration and ``easy(...).runtime()`` a fresh,
unentered :class:`~arkitekt.runtime.Runtime`.

These are for *calling* the API. An app that offers actions is declared with
:class:`~arkitekt.App` and provided with :func:`~arkitekt.run`.
"""

# The overloads are generated for 0..8 services. A TypeVarTuple cannot map
# `Service[T]` to `T` position by position, so spelling out each arity is the only
# way to type the unpacked clients.

import atexit
from types import TracebackType
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union, cast, overload

from arkitekt_spec.declare.service import Service
from fakts.grants.remote.authorizers.device_code import DeviceCodeHook
from fakts.mesh import MeshOptions, MeshProxy
from koil import Koil

from arkitekt.app.app import App, _caller_module_name
from arkitekt.runtime import Runtime, connect

R = TypeVar("R")
T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")
T4 = TypeVar("T4")
T5 = TypeVar("T5")
T6 = TypeVar("T6")
T7 = TypeVar("T7")
T8 = TypeVar("T8")


class Easy(Generic[R]):
    """An app declared for a script, and how to connect it. Enter it for its clients.

    ``with`` and ``async with`` both work, each entering a fresh runtime, so one
    ``Easy`` can be entered again (or nested) without two uses sharing a connection.

    Args:
        app: The app declared for the script.
        services: The services whose clients to hand back, in order.
        connection: The keywords :func:`~arkitekt.connect` is called with.

    Attributes:
        app: The app declared for the script.
        services: The services whose clients are handed back, in order.
    """

    def __init__(
        self, app: App[Any], services: tuple["Service[Any]", ...], connection: Dict[str, Any]
    ) -> None:
        self.app = app
        self.services = services
        self._connection = connection
        self._runtimes: List[Runtime[Any]] = []

    def __repr__(self) -> str:
        names = ", ".join(declared.name for declared in self.services)
        return f"Easy({self.app.identifier!r}, {names})"

    def runtime(self) -> Runtime[Any]:
        """Make a fresh runtime for the app, connected the way this was configured.

        Returns:
            The runtime, not yet entered.
        """
        return connect(self.app, **self._connection)

    def resolve(self, runtime: Runtime[Any]) -> R:
        """Pick the named clients out of an entered runtime.

        Args:
            runtime: An entered runtime of :attr:`app`.

        Returns:
            ``None`` for no services, the client for one, a tuple for several.

        Raises:
            LookupError: If the runtime has no client for a named service.
        """
        found: tuple[Any, ...] = tuple(
            self._client_of(runtime, declared) for declared in self.services
        )
        if not found:
            return cast(R, None)
        if len(found) == 1:
            return cast(R, found[0])
        return cast(R, found)

    @staticmethod
    def _client_of(runtime: Runtime[Any], declared: "Service[Any]") -> Any:  # noqa: ANN401
        try:
            return runtime.clients[declared.name]
        except KeyError:
            raise LookupError(
                f"This run built no client for the service {declared.name!r}. It "
                f"uses: {', '.join(runtime.services) or 'no services'}."
            ) from None

    def __enter__(self) -> R:
        """Connect a fresh runtime and hand back the clients.

        Returns:
            The clients; see :meth:`resolve`.
        """
        runtime = self.runtime()
        runtime.__enter__()
        self._runtimes.append(runtime)
        return self.resolve(runtime)

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Close the runtime the matching ``with`` opened.

        Args:
            exc_type: The type of the exception leaving the block, if any.
            exc_value: The exception leaving the block, if any.
            traceback: Its traceback, if any.
        """
        self._runtimes.pop().__exit__(exc_type, exc_value, traceback)

    async def __aenter__(self) -> R:
        """Connect a fresh runtime and hand back the clients, asynchronously.

        Returns:
            The clients; see :meth:`resolve`.
        """
        runtime = self.runtime()
        await runtime.__aenter__()
        self._runtimes.append(runtime)
        return self.resolve(runtime)

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Close the runtime the matching ``async with`` opened.

        Args:
            exc_type: The type of the exception leaving the block, if any.
            exc_value: The exception leaving the block, if any.
            traceback: Its traceback, if any.
        """
        await self._runtimes.pop().__aexit__(exc_type, exc_value, traceback)


def _build(
    identifier: Optional[str],
    services: tuple["Service[Any]", ...],
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> "Easy[Any]":
    # Three frames up: the caller of easy()/aeasy()/interactive(), not this module.
    app = App(
        identifier or _caller_module_name(3),
        version,
        logo=logo,
        scopes=scopes,
        author=author,
        services=list(services),
    )
    connection: Dict[str, Any] = dict(
        url=url,
        token=token,
        redeem_token=redeem_token,
        no_cache=no_cache,
        headless=headless,
        device_code_hook=device_code_hook,
        force=force,
        device_id=device_id,
        mesh=mesh,
    )
    return Easy(app, services, connection)


@overload
def easy(
    identifier: Optional[str] = None,
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[None]: ...


@overload
def easy(
    identifier: Optional[str],
    s1: Service[T1],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[T1]: ...


@overload
def easy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2]]: ...


@overload
def easy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2, T3]]: ...


@overload
def easy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2, T3, T4]]: ...


@overload
def easy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4], s5: Service[T5],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2, T3, T4, T5]]: ...


@overload
def easy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4], s5: Service[T5], s6: Service[T6],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2, T3, T4, T5, T6]]: ...


@overload
def easy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4], s5: Service[T5], s6: Service[T6], s7: Service[T7],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2, T3, T4, T5, T6, T7]]: ...


@overload
def easy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4], s5: Service[T5], s6: Service[T6], s7: Service[T7], s8: Service[T8],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2, T3, T4, T5, T6, T7, T8]]: ...


def easy(
    identifier: Optional[str] = None,
    /,
    *services: "Service[Any]",
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> "Easy[Any]":
    """Declare an app using these clients' services; enter it for the clients.

    Nothing connects until it is entered. ``with easy("x", mikro_service) as mikro:``.

    Args:
        identifier: The app's identifier. Defaults to the calling file's name.
        *services: The services to use, whose clients are handed back in order.
        version: The app's version.
        logo: A public http url of the app's logo.
        scopes: The scopes the app requests. Defaults to ``["openid"]``.
        author: Who wrote the app.
        url: The fakts server. Defaults to ``$FAKTS_URL``, then the public
            deployment.
        token: A previously issued credential, ``client_id:refresh_token``.
        redeem_token: A token to provision a new app with.
        no_cache: Skip the fakts cache, and so authenticate again.
        headless: Print the device-code prompt instead of opening a browser.
        device_code_hook: Called with the device code instead of the default prompt.
        force: Take over an existing agent connection of this app.
        device_id: The machine's identity. Defaults to one stored for this machine.
        mesh: How to reach services only on the deployment's mesh:
            ``MeshOptions()`` or ``True`` runs a node in this process (``arkitekt[mesh]``),
            ``MeshProxy(url=...)`` goes through a running proxy, ``False`` is off.
            Defaults to ``$ARKITEKT_MESH_PROXY``, then ``$ARKITEKT_MESH``; unset, the
            mesh is used when it is available (see :func:`arkitekt.app.fakts.mesh_from_env`).

    Returns:
        An :class:`Easy`: enter it for the clients -- ``None`` for no classes,
        the client for one, a tuple for several.

    Raises:
        TypeError: If something other than a service is given.
    """
    return _build(
        identifier,
        services,
        version=version,
        logo=logo,
        scopes=scopes,
        author=author,
        url=url,
        token=token,
        redeem_token=redeem_token,
        no_cache=no_cache,
        headless=headless,
        device_code_hook=device_code_hook,
        force=force,
        device_id=device_id,
        mesh=mesh,
    )


@overload
def aeasy(
    identifier: Optional[str] = None,
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[None]: ...


@overload
def aeasy(
    identifier: Optional[str],
    s1: Service[T1],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[T1]: ...


@overload
def aeasy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2]]: ...


@overload
def aeasy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2, T3]]: ...


@overload
def aeasy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2, T3, T4]]: ...


@overload
def aeasy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4], s5: Service[T5],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2, T3, T4, T5]]: ...


@overload
def aeasy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4], s5: Service[T5], s6: Service[T6],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2, T3, T4, T5, T6]]: ...


@overload
def aeasy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4], s5: Service[T5], s6: Service[T6], s7: Service[T7],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2, T3, T4, T5, T6, T7]]: ...


@overload
def aeasy(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4], s5: Service[T5], s6: Service[T6], s7: Service[T7], s8: Service[T8],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Easy[tuple[T1, T2, T3, T4, T5, T6, T7, T8]]: ...


def aeasy(
    identifier: Optional[str] = None,
    /,
    *services: "Service[Any]",
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> "Easy[Any]":
    """Declare an app using these clients' services; enter it for the clients.

    :func:`easy`, for ``async with``: ``async with aeasy("x", mikro_service) as mikro:``.

    Args:
        identifier: The app's identifier. Defaults to the calling file's name.
        *services: The services to use, whose clients are handed back in order.
        version: The app's version.
        logo: A public http url of the app's logo.
        scopes: The scopes the app requests. Defaults to ``["openid"]``.
        author: Who wrote the app.
        url: The fakts server. Defaults to ``$FAKTS_URL``, then the public
            deployment.
        token: A previously issued credential, ``client_id:refresh_token``.
        redeem_token: A token to provision a new app with.
        no_cache: Skip the fakts cache, and so authenticate again.
        headless: Print the device-code prompt instead of opening a browser.
        device_code_hook: Called with the device code instead of the default prompt.
        force: Take over an existing agent connection of this app.
        device_id: The machine's identity. Defaults to one stored for this machine.
        mesh: How to reach services only on the deployment's mesh:
            ``MeshOptions()`` or ``True`` runs a node in this process (``arkitekt[mesh]``),
            ``MeshProxy(url=...)`` goes through a running proxy, ``False`` is off.
            Defaults to ``$ARKITEKT_MESH_PROXY``, then ``$ARKITEKT_MESH``; unset, the
            mesh is used when it is available (see :func:`arkitekt.app.fakts.mesh_from_env`).

    Returns:
        An :class:`Easy`: enter it for the clients -- ``None`` for no classes,
        the client for one, a tuple for several.

    Raises:
        TypeError: If something other than a service is given.
    """
    return _build(
        identifier,
        services,
        version=version,
        logo=logo,
        scopes=scopes,
        author=author,
        url=url,
        token=token,
        redeem_token=redeem_token,
        no_cache=no_cache,
        headless=headless,
        device_code_hook=device_code_hook,
        force=force,
        device_id=device_id,
        mesh=mesh,
    )


#: Runtimes entered by :func:`interactive`, by app identifier: one per app, left when
#: the process exits.
_interactive_runtimes: Dict[str, Runtime[Any]] = {}


def _leave_interactive(identifier: Optional[str] = None) -> None:
    """Leave the runtime :func:`interactive` entered for ``identifier``, or every one.

    Args:
        identifier: The app whose runtime to leave. ``None`` leaves all of them,
            newest first, which is what happens when the process exits.
    """
    names = [identifier] if identifier is not None else list(reversed(_interactive_runtimes))
    for name in names:
        runtime = _interactive_runtimes.pop(name, None)
        if runtime is None:
            continue
        try:
            runtime.__exit__(None, None, None)
        except Exception:  # noqa: BLE001 -- the process may be exiting anyway
            pass


atexit.register(_leave_interactive)


@overload
def interactive(
    identifier: Optional[str] = None,
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> None: ...


@overload
def interactive(
    identifier: Optional[str],
    s1: Service[T1],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> T1: ...


@overload
def interactive(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> tuple[T1, T2]: ...


@overload
def interactive(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> tuple[T1, T2, T3]: ...


@overload
def interactive(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> tuple[T1, T2, T3, T4]: ...


@overload
def interactive(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4], s5: Service[T5],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> tuple[T1, T2, T3, T4, T5]: ...


@overload
def interactive(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4], s5: Service[T5], s6: Service[T6],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> tuple[T1, T2, T3, T4, T5, T6]: ...


@overload
def interactive(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4], s5: Service[T5], s6: Service[T6], s7: Service[T7],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> tuple[T1, T2, T3, T4, T5, T6, T7]: ...


@overload
def interactive(
    identifier: Optional[str],
    s1: Service[T1], s2: Service[T2], s3: Service[T3], s4: Service[T4], s5: Service[T5], s6: Service[T6], s7: Service[T7], s8: Service[T8],
    /,
    *,
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8]: ...


def interactive(
    identifier: Optional[str] = None,
    /,
    *services: "Service[Any]",
    version: str = "0.0.1",
    logo: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Any:  # noqa: ANN401 -- typed by the overloads
    """Connect and stay connected; return the clients. For notebooks.

    ``mikro, fluss = interactive("notebook", mikro_service, fluss_service)``. Sync calls work inside
    Jupyter's running event loop. The connection is left when the process exits, or
    when this is called again for the same identifier.

    Args:
        identifier: The app's identifier. Defaults to the calling file's name.
        *services: The services to use, whose clients are handed back in order.
        version: The app's version.
        logo: A public http url of the app's logo.
        scopes: The scopes the app requests. Defaults to ``["openid"]``.
        author: Who wrote the app.
        url: The fakts server. Defaults to ``$FAKTS_URL``, then the public
            deployment.
        token: A previously issued credential, ``client_id:refresh_token``.
        redeem_token: A token to provision a new app with.
        no_cache: Skip the fakts cache, and so authenticate again.
        headless: Print the device-code prompt instead of opening a browser.
        device_code_hook: Called with the device code instead of the default prompt.
        force: Take over an existing agent connection of this app.
        device_id: The machine's identity. Defaults to one stored for this machine.
        mesh: How to reach services only on the deployment's mesh:
            ``MeshOptions()`` or ``True`` runs a node in this process (``arkitekt[mesh]``),
            ``MeshProxy(url=...)`` goes through a running proxy, ``False`` is off.
            Defaults to ``$ARKITEKT_MESH_PROXY``, then ``$ARKITEKT_MESH``; unset, the
            mesh is used when it is available (see :func:`arkitekt.app.fakts.mesh_from_env`).

    Returns:
        ``None`` for no classes, the client for one, a tuple for several.

    Raises:
        TypeError: If something other than a service is given.
    """
    shortcut = _build(
        identifier,
        services,
        version=version,
        logo=logo,
        scopes=scopes,
        author=author,
        url=url,
        token=token,
        redeem_token=redeem_token,
        no_cache=no_cache,
        headless=headless,
        device_code_hook=device_code_hook,
        force=force,
        device_id=device_id,
        mesh=mesh,
    )
    # One connection per app: calling this again for the same identifier (a
    # re-run notebook cell) leaves the previous one instead of piling them up.
    _leave_interactive(shortcut.app.identifier)
    runtime = shortcut.runtime()
    # A notebook runs its own event loop; let sync calls run inside it.
    setattr(runtime, "__koil", Koil(sync_in_async=True))
    runtime.enter()
    _interactive_runtimes[shortcut.app.identifier] = runtime
    return shortcut.resolve(runtime)


__all__ = ["Easy", "easy", "aeasy", "interactive"]
