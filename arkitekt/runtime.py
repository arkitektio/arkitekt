"""Running an app: everything stateful lives here, never on the :class:`~arkitekt.App`.

``run(app)`` connects and provides until stopped. ``connect(app)`` only connects,
for a script that calls the API::

    with connect(app) as rt:
        mikro = rt.require(Mikro)
        segment(image, mikro=mikro, task=Task.local())

Each of them builds a fresh :class:`Runtime`: a snapshot of the app's registry,
fakts, a manifest carrying this machine's node id, and one client per service.
How to connect (url, tokens, ...) is an argument of the run, not part of the app.
"""

import asyncio
import logging
import threading
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Mapping,
    Optional,
    Self,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from arkitekt_spec.declare.agents.connection import ConnectionState
from arkitekt_spec.declare.provider import Provider
from arkitekt_spec.declare.service import Service
from fakts import Fakts, oauth2
from fakts.grants.remote.authorizers.device_code import DeviceCodeChallenge, DeviceCodeHook
from fakts.grants.remote.discovery.well_known import WellKnownDiscovery
from fakts.grants.remote.models import SSLContextModel
from fakts.mesh import MeshOptions, MeshProxy
from koil import unkoil
from koil.bridge import unkoil_task
from koil.composition import KoiledModel
from pydantic import ConfigDict, Field, PrivateAttr

from arkitekt.app.app import App, Ctx
from arkitekt.app.fakts import build_fakts, resolve_url
from arkitekt.app.options import ConnectionOptions
from arkitekt.app.sessions import forget, read_credentials, read_session, session_path
from arkitekt.app.snapshot import RunSnapshot
from arkitekt.device_id import get_or_set_device_id

if TYPE_CHECKING:
    from arkitekt_spec.declare.agents.connection import ConnectionListener, TaskListener
    from fakts.models import ActiveFakts, AuthFakt, Manifest
    from koil import KoilFuture


logger = logging.getLogger(__name__)

T = TypeVar("T")


class Runtime(KoiledModel, Generic[Ctx]):
    """One run of an app: its fakts, clients and registry snapshot.

    Built by :func:`connect` and :func:`run`. Entering it takes the snapshot,
    builds fakts if anything needs it, builds one client per service, then the
    app's agent from its provider, and enters them all; leaving it closes
    everything. A runtime is used once -- connect again for a second run; the
    app is unchanged by the first.

    It is also what an action's injected clients come from: :meth:`get`. The
    agent is the runtime's: it is bound to this run, takes the run's options and
    is driven by :meth:`arun`.

    A run leaves the process as it found it: it configures no logging, writes
    nothing into the working directory, and holds nothing outside itself.

    Attributes:
        app: The app this is a run of. The declaration, unchanged by the run;
            what the run actually serves is :attr:`snapshot`.
        options: How it connects.
        snapshot: What this run serves: its manifest, its frozen registry and
            its services, taken together. Set when entered.
        fakts: The run's fakts. Set when entered, and only when a service or the
            provider needs one: a run of an app with no requirements
            authenticates nothing.
        clients: The run's built clients, by service name. Empty until entered.
        agent: The agent providing the app's offerings, built from ``provider``
            when entered. ``None`` for a run that provides nothing.
        provider: What this run builds its agent from: ``None`` for
            :func:`connect`, the app's own or rekuest's for :func:`run`, the
            FastAPI one for :func:`~arkitekt.serve`. Taken into the run's
            registry and manifest by :meth:`~arkitekt.App.snapshot`.
    """

    app: App[Ctx]
    options: ConnectionOptions = Field(default_factory=ConnectionOptions)
    snapshot: Optional[RunSnapshot] = None
    fakts: Optional[Fakts] = None
    clients: Dict[str, Any] = Field(default_factory=dict)
    # ``Any``: an agent is an ``AgentLifecycle``, a Protocol with a data member,
    # which pydantic cannot validate against.
    agent: Optional[Any] = None
    provider: Optional[Any] = Field(default=None, exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    _entered: List[Any] = PrivateAttr(default_factory=list)
    _used: bool = PrivateAttr(default=False)

    # ------------------------------------------------------------------ #
    # Clients                                                            #
    # ------------------------------------------------------------------ #

    @property
    def services(self) -> Mapping[str, "Service[Any]"]:
        """The services this run declares, by name.

        The *declared* services, not the built clients: this is what rekuest's
        ``BoundApp`` protocol reads to warn about a structure whose service the
        app lacks, which is a question about the declaration. Empty until entered.
        """
        return self.snapshot.services if self.snapshot is not None else {}

    def get(self, cls: Type[T]) -> Optional[T]:
        """Find this run's client of class ``cls``.

        Whatever a service's function returned is its client, so the match is
        by instance.

        Args:
            cls: The client class, e.g. ``Mikro``.

        Returns:
            The client, or ``None`` if no service of this run returned one.
        """
        for client in self.clients.values():
            if isinstance(client, cls):
                return cast(T, client)
        return None

    def require(self, cls: Type[T]) -> T:
        """Get this run's client of class ``cls``.

        Args:
            cls: The client class, e.g. ``Mikro``.

        Returns:
            The client.

        Raises:
            LookupError: If the app uses no service building one.
        """
        client = self.get(cls)
        if client is None:
            raise LookupError(
                f"This run has no {cls.__name__}. The app uses: "
                f"{', '.join(self.services) or 'no services'}. Register the service "
                f"that builds it: `app.service({cls.__name__.lower()}_service)`."
            )
        return client

    # ------------------------------------------------------------------ #
    # Building                                                           #
    # ------------------------------------------------------------------ #

    def _prepare(self) -> RunSnapshot:
        """Take the snapshot, with this run's provider in it. Nothing connects yet.

        Taking it validates the declaration, before anything connects: a port
        naming a structure this app cannot resolve would otherwise fail
        mid-assignment, far from its cause.
        """
        device_id = self.options.device_id or get_or_set_device_id()
        return self.app.snapshot(device_id=device_id, provider=self.provider)

    def _needs_fakts(self, snapshot: RunSnapshot) -> bool:
        """Whether anything this run builds resolves through fakts."""
        return any(service.needs_fakts for service in snapshot.services.values()) or (
            self.provider is not None and self.provider.needs_fakts
        )

    async def _build_clients(
        self, snapshot: RunSnapshot, fakts: Optional[Fakts]
    ) -> Dict[str, Any]:
        """Resolve each service's requirements and build its client.

        Runs after fakts is entered: a service is handed the *resolved* address of
        each thing it requires, which needs a loaded configuration. An unreachable
        required service therefore fails here, while the run is still connecting,
        rather than on the first call that happens to need it.
        """
        clients: Dict[str, Any] = {}
        for name, builder in snapshot.services.items():
            # Each service takes only what its signature asks for; there is no
            # bag of parameters every builder has to know about.
            client = await builder.build(fakts, snapshot.registry)
            if client is not None:
                clients[name] = client

        # Set before binding: the runtime *is* the BoundApp the structures bind
        # from, and a structure's expander finds its client by class through it.
        self.clients = clients

        # The snapshot owns its structure maps, so binding here never reaches the
        # app.
        snapshot.registry.structure_registry.bind(self)
        return clients

    async def _build_agent(
        self, snapshot: RunSnapshot, fakts: Optional[Fakts]
    ) -> Optional[Any]:
        """Build the agent from this run's provider, after the clients, and make it this run's."""
        provider = self.provider
        if provider is None:
            return None
        agent = await provider.build(fakts, snapshot.registry, self.clients)
        # Bound before entered: the agent reads `bound_app` while registering.
        agent.bound_app = self
        agent.force = self.options.force
        # Only when given: an agent that takes no listener is left as it was built.
        for name in ("connection_listener", "task_listener"):
            listener = getattr(self.options, name)
            if listener is None:
                continue
            try:
                setattr(agent, name, listener)
            except (AttributeError, ValueError):
                # An agent of a runtime that predates the listener: the run goes
                # on, it just has nobody to report to.
                logger.debug("%r takes no %s", type(agent).__name__, name)
        return agent

    # ------------------------------------------------------------------ #
    # Entering                                                           #
    # ------------------------------------------------------------------ #

    async def __aenter__(self) -> Self:
        """Build and connect everything: snapshot, fakts, resolve, then each client.

        Returns:
            The runtime, entered.

        Raises:
            RuntimeError: If this runtime was entered before.
            StructureRegistryError: If the app's registry does not validate.
        """

        if self._used:
            raise RuntimeError(
                "This runtime was already used. Connect again for another run: "
                "`connect(app)` -- the app itself is unchanged by a run."
            )
        self._used = True

        snapshot = self._prepare()
        self.snapshot = snapshot
        try:
            if self._needs_fakts(snapshot):
                # Fakts first: a service is handed its resolved address, and
                # resolving one needs a loaded configuration.
                self.fakts = build_fakts(snapshot.manifest, self.options)
                await self.fakts.__aenter__()
                self._entered.append(self.fakts)
            self.clients = await self._build_clients(snapshot, self.fakts)
            self.agent = await self._build_agent(snapshot, self.fakts)
            for client in self.clients.values():
                if hasattr(client, "__aenter__"):
                    await client.__aenter__()
                    self._entered.append(client)
            # After the clients, so it closes first. Its socket opens only when it
            # provides (`arun`): entering it connects nothing.
            if self.agent is not None and hasattr(self.agent, "__aenter__"):
                await self.agent.__aenter__()
                self._entered.append(self.agent)
        except BaseException as e:
            await self._exit_entered(type(e), e, e.__traceback__)
            raise
        return self

    async def _exit_entered(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        while self._entered:
            part = self._entered.pop()
            try:
                await part.__aexit__(exc_type, exc_value, traceback)
            except Exception:
                logger.exception("Failed to close %r while leaving the runtime", part)

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Close every client, then fakts, in reverse order of entering.

        Args:
            exc_type: The type of the exception leaving the block, if any.
            exc_value: The exception leaving the block, if any.
            traceback: Its traceback, if any.
        """
        await self._exit_entered(exc_type, exc_value, traceback)

    # ------------------------------------------------------------------ #
    # Running                                                            #
    # ------------------------------------------------------------------ #

    def _require_agent(self) -> Any:  # noqa: ANN401
        if self.agent is None:
            if self.app.registry.is_empty():
                raise LookupError(
                    "This app offers nothing, so there is nothing to provide: no "
                    "action, state, hook or blok. Use `connect(app)` to only call the API."
                )
            raise LookupError(
                "This runtime was connected without providing. Use `run(app)`, or "
                "`connect(app, provide=True)` for a runtime that provides on `run()`."
            )
        return self.agent

    def _require_context(self, context: Any) -> None:  # noqa: ANN401
        self.app.registry.require_app_context(context, whose=f"App {self.app.identifier!r}")

    @overload
    async def arun(self: "Runtime[None]", context: None = None) -> None: ...
    @overload
    async def arun(self, context: Ctx) -> None: ...

    async def arun(self, context: Optional[Ctx] = None) -> None:
        """Run the app until stopped: provide its offerings. The runtime must be entered.

        Args:
            context: The app context: an instance of the class the app declared
                (``App(..., app_context=Config)``), handed to the hooks and
                actions that ask for it. Nothing for an app that declares none.

        Raises:
            AppContextError: If ``context`` is not what the app declared.
            LookupError: If the app offers nothing.
        """
        self._require_context(context)
        await self._aprovide(context)

    async def _aprovide(self, context: Optional[Ctx]) -> None:
        """Provide the app's offerings with ``context``, already checked by the caller."""
        await self._require_agent().aprovide(context=context)

    @overload
    def run(self: "Runtime[None]", context: None = None) -> None: ...
    @overload
    def run(self, context: Ctx) -> None: ...

    def run(self, context: Optional[Ctx] = None) -> None:
        """Run the app until stopped: provide its offerings. The runtime must be entered.

        Raises:
            AppContextError: If ``context`` is not what the app declared.
            LookupError: If the app offers nothing.
        """
        self._require_context(context)
        unkoil(self._aprovide, context)

    @overload
    def run_detached(self: "Runtime[None]", context: None = None) -> "KoilFuture[None]": ...
    @overload
    def run_detached(self, context: Ctx) -> "KoilFuture[None]": ...

    def run_detached(self, context: Optional[Ctx] = None) -> "KoilFuture[None]":
        """Start running in the background.

        Returns:
            A future that completes when the run stops.

        Raises:
            AppContextError: If ``context`` is not what the app declared; at the
                call, not in the future.
            LookupError: If the app offers nothing.
        """
        self._require_context(context)
        self._require_agent()
        return unkoil_task(self._aprovide, context)


#: What ``run()`` says when an app offers something and no runtime is installed.
NO_RUNTIME_HINT = (
    "This app offers actions, states or bloks, and running it needs a runtime that is "
    "not installed. Install rekuest (pip install 'arkitekt[rekuest]') to run it in "
    "distributed mode, or serve it with `serve(app, fastapi_app)` (arkitekt[serve])."
)


class RuntimeNotInstalledError(ImportError):
    """``run()`` was asked to serve an app, and no runtime (rekuest) is installed."""


def _provider_for(app: App[Any], *, required: bool = True) -> Optional[Provider[Any]]:
    """The provider a run of ``app`` builds its agent from: the app's own, or rekuest's.

    An app offering anything without declaring how it is served is served by
    rekuest; one offering nothing is not served at all. rekuest is not a dependency
    of arkitekt: when it is missing, a run (``required``) raises
    :class:`RuntimeNotInstalledError`, and an inspection gets ``None`` -- the app as
    declared, without the requirements rekuest's provider would add.
    """
    declared = app.registry.provider_declaration
    if declared is not None:
        return declared
    if app.registry.is_empty():
        return None
    try:
        from rekuest.arkitekt import rekuest_provider
    except ImportError as e:
        if required:
            raise RuntimeNotInstalledError(NO_RUNTIME_HINT) from e
        return None
    return rekuest_provider


def connect(
    app: App[Ctx],
    *,
    provide: bool = False,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    connection_listener: Optional["ConnectionListener"] = None,
    task_listener: Optional["TaskListener"] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> Runtime[Ctx]:
    """Make a runtime for ``app`` that connects when entered.

    For scripts and notebooks that call the API::

        with connect(app) as rt:
            mikro = rt.require(Mikro)

        rt = connect(app).enter()      # notebook: stays connected

    With ``provide=True`` the runtime also builds the app's agent -- from the
    provider it declares, or rekuest's if it offers anything -- and provides
    on :meth:`Runtime.run`; that is what :func:`run` does.

    Args:
        app: The app to run.
        provide: Whether the runtime builds an agent to provide the app's
            offerings with. Off for a script that only calls the API.
        url: The fakts server. Defaults to ``$FAKTS_URL``, then the public
            deployment.
        token: A previously issued credential, ``client_id:refresh_token``.
            Defaults to ``$FAKTS_TOKEN``.
        redeem_token: A token to provision a new app with. Defaults to
            ``$FAKTS_REDEEM_TOKEN``.
        skip_cache: Neither read nor write the fakts cache: log in, and keep the
            session in memory only.
        reauth: Log in again even when a session is cached, and cache the new
            one. Defaults to ``$ARKITEKT_REAUTH``.
        headless: Print the device-code prompt instead of opening a browser.
        device_code_hook: Called with the login to approve -- a
            :class:`~arkitekt.DeviceCodeChallenge` carrying the code and the link --
            instead of the terminal prompt. With ``headless`` nothing is printed
            or opened: showing the login is the hook's.
        force: Take over an existing agent connection of this app.
        connection_listener: Told when the server acknowledges the app's agent and
            when the link to it drops.
        task_listener: Told what happens to each task the app's agent takes: a
            :class:`~arkitekt.TaskEvent` when it is assigned (with its arguments),
            reports progress, yields, and ends done, failed or cancelled.
        allow_insecure_transport: Talk plain http to a server that is not on this
            machine. Off, such a server is refused.
        device_id: This device's identity. Defaults to the machine's id.
        mesh: How to reach services only on the deployment's mesh:
            ``MeshOptions()`` or ``True`` runs a node in this process (``arkitekt[mesh]``),
            ``MeshProxy(url=...)`` goes through a running proxy, ``False`` is off.
            Defaults to ``$ARKITEKT_MESH_PROXY``, then ``$ARKITEKT_MESH``; unset, the
            mesh is used when it is available (see :func:`arkitekt.app.fakts.mesh_from_env`).

    Returns:
        The runtime, not yet entered.
    """
    return Runtime(
        app=app,
        options=ConnectionOptions(
            url=url,
            token=token,
            redeem_token=redeem_token,
            skip_cache=skip_cache,
            reauth=reauth,
            headless=headless,
            device_code_hook=device_code_hook,
            force=force,
            connection_listener=connection_listener,
            task_listener=task_listener,
            allow_insecure_transport=allow_insecure_transport,
            device_id=device_id,
            mesh=mesh,
        ),
        provider=_provider_for(app) if provide else None,
    )


@overload
def run(
    app: App[None],
    *,
    context: None = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    connection_listener: Optional["ConnectionListener"] = None,
    task_listener: Optional["TaskListener"] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> None: ...
@overload
def run(
    app: App[Ctx],
    *,
    context: Ctx,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    connection_listener: Optional["ConnectionListener"] = None,
    task_listener: Optional["TaskListener"] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> None: ...


def run(
    app: App[Any],
    *,
    context: Any | None = None,  # noqa: ANN401
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    connection_listener: Optional["ConnectionListener"] = None,
    task_listener: Optional["TaskListener"] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> None:
    """Connect ``app`` and provide its offerings until stopped: the rekuest runtime.

    The app is served through the provider it declares, or rekuest's.

    ::

        if __name__ == "__main__":
            run(app, context=Config())

    Args:
        app: The app to provide.
        context: The app context: an instance of the class the app declared
            (``App(..., app_context=Config)``), handed to the hooks and actions
            that ask for it. Required then; nothing for an app declaring none.
        url: The fakts server. Defaults to ``$FAKTS_URL``, then the public
            deployment.
        token: A previously issued credential, ``client_id:refresh_token``.
            Defaults to ``$FAKTS_TOKEN``.
        redeem_token: A token to provision a new app with. Defaults to
            ``$FAKTS_REDEEM_TOKEN``.
        skip_cache: Neither read nor write the fakts cache: log in, and keep the
            session in memory only.
        reauth: Log in again even when a session is cached, and cache the new
            one. Defaults to ``$ARKITEKT_REAUTH``.
        headless: Print the device-code prompt instead of opening a browser.
        device_code_hook: Called with the login to approve -- a
            :class:`~arkitekt.DeviceCodeChallenge` carrying the code and the link --
            instead of the terminal prompt. With ``headless`` nothing is printed
            or opened: showing the login is the hook's.
        force: Take over an existing agent connection of this app.
        connection_listener: Told when the server acknowledges the app's agent and
            when the link to it drops.
        task_listener: Told what happens to each task the app's agent takes: a
            :class:`~arkitekt.TaskEvent` when it is assigned (with its arguments),
            reports progress, yields, and ends done, failed or cancelled.
        allow_insecure_transport: Talk plain http to a server that is not on this
            machine. Off, such a server is refused.
        device_id: This device's identity. Defaults to the machine's id.
        mesh: How to reach services only on the deployment's mesh:
            ``MeshOptions()`` or ``True`` runs a node in this process (``arkitekt[mesh]``),
            ``MeshProxy(url=...)`` goes through a running proxy, ``False`` is off.
            Defaults to ``$ARKITEKT_MESH_PROXY``, then ``$ARKITEKT_MESH``; unset, the
            mesh is used when it is available (see :func:`arkitekt.app.fakts.mesh_from_env`).

    Raises:
        AppContextError: If ``context`` is not what the app declared. Raised
            before anything connects or logs in.
        LookupError: If the app offers nothing.
    """
    app.registry.require_app_context(context, whose=f"App {app.identifier!r}")
    runtime = connect(
        app,
        provide=True,
        url=url,
        token=token,
        redeem_token=redeem_token,
        skip_cache=skip_cache,
        reauth=reauth,
        headless=headless,
        device_code_hook=device_code_hook,
        force=force,
        connection_listener=connection_listener,
        task_listener=task_listener,
        allow_insecure_transport=allow_insecure_transport,
        device_id=device_id,
        mesh=mesh,
    )
    # Entered synchronously, around the unkoil rather than inside it: koil
    # establishes its loop when the runtime is entered.
    with runtime:
        runtime.run(context=context)


@overload
async def arun(
    app: App[None],
    *,
    context: None = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    connection_listener: Optional["ConnectionListener"] = None,
    task_listener: Optional["TaskListener"] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> None: ...
@overload
async def arun(
    app: App[Ctx],
    *,
    context: Ctx,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    connection_listener: Optional["ConnectionListener"] = None,
    task_listener: Optional["TaskListener"] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> None: ...


async def arun(
    app: App[Any],
    *,
    context: Any | None = None,  # noqa: ANN401
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    connection_listener: Optional["ConnectionListener"] = None,
    task_listener: Optional["TaskListener"] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> None:
    """Connect ``app`` and provide its actions until stopped, asynchronously.

    Args:
        app: The app to provide.
        context: The app context, as for :func:`run`.
        url: The fakts server. Defaults to ``$FAKTS_URL``, then the public
            deployment.
        token: A previously issued credential, ``client_id:refresh_token``.
            Defaults to ``$FAKTS_TOKEN``.
        redeem_token: A token to provision a new app with. Defaults to
            ``$FAKTS_REDEEM_TOKEN``.
        skip_cache: Neither read nor write the fakts cache: log in, and keep the
            session in memory only.
        reauth: Log in again even when a session is cached, and cache the new
            one. Defaults to ``$ARKITEKT_REAUTH``.
        headless: Print the device-code prompt instead of opening a browser.
        device_code_hook: Called with the login to approve -- a
            :class:`~arkitekt.DeviceCodeChallenge` carrying the code and the link --
            instead of the terminal prompt. With ``headless`` nothing is printed
            or opened: showing the login is the hook's.
        force: Take over an existing agent connection of this app.
        connection_listener: Told when the server acknowledges the app's agent and
            when the link to it drops.
        task_listener: Told what happens to each task the app's agent takes: a
            :class:`~arkitekt.TaskEvent` when it is assigned (with its arguments),
            reports progress, yields, and ends done, failed or cancelled.
        allow_insecure_transport: Talk plain http to a server that is not on this
            machine. Off, such a server is refused.
        device_id: This device's identity. Defaults to the machine's id.
        mesh: How to reach services only on the deployment's mesh:
            ``MeshOptions()`` or ``True`` runs a node in this process (``arkitekt[mesh]``),
            ``MeshProxy(url=...)`` goes through a running proxy, ``False`` is off.
            Defaults to ``$ARKITEKT_MESH_PROXY``, then ``$ARKITEKT_MESH``; unset, the
            mesh is used when it is available (see :func:`arkitekt.app.fakts.mesh_from_env`).

    Raises:
        AppContextError: If ``context`` is not what the app declared. Raised
            before anything connects or logs in.
        LookupError: If the app offers nothing.
    """
    app.registry.require_app_context(context, whose=f"App {app.identifier!r}")
    runtime = connect(
        app,
        provide=True,
        url=url,
        token=token,
        redeem_token=redeem_token,
        skip_cache=skip_cache,
        reauth=reauth,
        headless=headless,
        device_code_hook=device_code_hook,
        force=force,
        connection_listener=connection_listener,
        task_listener=task_listener,
        allow_insecure_transport=allow_insecure_transport,
        device_id=device_id,
        mesh=mesh,
    )
    async with runtime:
        await runtime.arun(context=context)


def run_manifest(app: App[Any], device_id: Optional[str] = None) -> "Manifest":
    """The manifest a run of ``app`` sends: what the server is asked to approve.

    A session is saved for exactly this manifest: an app declared differently
    (another scope, another service, another device) logs in again. It is the
    providing run's, so it carries what the app's provider requires too.

    Args:
        app: The app.
        device_id: This device's identity. Defaults to the machine's id.

    Returns:
        The manifest.
    """
    return connect(app, provide=True, device_id=device_id)._prepare().manifest


async def alogin(
    app: App[Any],
    *,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
) -> "ActiveFakts":
    """Log ``app`` in and cache the session, without connecting anything else.

    What a run does first, on its own: no client is built and no agent, so a
    service that is down does not stand in the way of logging in. It logs in as
    the run would -- with the manifest the run sends, its provider's requirements
    included -- so the session saved is the one the run finds.

    Args:
        app: The app to log in.
        url: The fakts server. Defaults to ``$FAKTS_URL``, then the public
            deployment.
        token: A previously issued credential, ``client_id:refresh_token``.
            Defaults to ``$FAKTS_TOKEN``.
        redeem_token: A token to provision a new app with. Defaults to
            ``$FAKTS_REDEEM_TOKEN``.
        skip_cache: Neither read nor write the fakts cache.
        reauth: Log in again even when a session is cached, and cache the new
            one. Defaults to ``$ARKITEKT_REAUTH``.
        headless: Print the device-code prompt instead of opening a browser.
        device_code_hook: Called with the login to approve -- a
            :class:`~arkitekt.DeviceCodeChallenge` carrying the code and the link --
            instead of the terminal prompt. With ``headless`` nothing is printed
            or opened: showing the login is the hook's.
        allow_insecure_transport: Talk plain http to a server that is not on this
            machine. Off, such a server is refused.
        device_id: This device's identity. Defaults to the machine's id.

    Returns:
        The session the app is logged in with.
    """
    options = ConnectionOptions(
        url=url,
        token=token,
        redeem_token=redeem_token,
        skip_cache=skip_cache,
        reauth=reauth,
        headless=headless,
        device_code_hook=device_code_hook,
        allow_insecure_transport=allow_insecure_transport,
        device_id=device_id,
    )
    fakts = build_fakts(run_manifest(app, device_id=device_id), options)
    async with fakts:
        return await fakts.aload()


class DetachedRun(Generic[Ctx]):
    """A run of an app on a thread of its own: what :func:`run_detached` returns.

    For a program that has a life of its own -- a control program, a GUI, a
    server -- and offers an app beside it. The run owns its thread and its event
    loop, so the host needs neither: it starts the run, is told where it stands,
    and cancels it, from any thread.

    Attributes:
        app: The app this runs.
    """

    def __init__(
        self,
        app: App[Ctx],
        context: Optional[Ctx],
        options: ConnectionOptions,
    ) -> None:
        self.app = app
        self._context = context
        self._options = options
        self._state = ConnectionState.STOPPED
        self._error: Optional[BaseException] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._task: Optional["asyncio.Task[None]"] = None
        self._guard = threading.Lock()

    @property
    def state(self) -> ConnectionState:
        """Where the run stands. ``connection_listener`` is told every change of it."""
        return self._state

    @property
    def error(self) -> Optional[BaseException]:
        """What ended the run, when its state is ``FAILED``."""
        return self._error

    def start(self) -> None:
        """Start the run; returns at once. :func:`run_detached` already did this once.

        Call it again after a cancel or a failure to run with the same settings.

        Raises:
            RuntimeError: If the run is still going.
            RuntimeNotInstalledError: If the app offers something and no runtime
                is installed.
        """
        with self._guard:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError(
                    f"This run of {self.app.identifier!r} is still going "
                    f"({self._state.value}). Cancel it before starting it again."
                )
            # Built here, not on the thread: what is wrong with the app or the
            # installation is raised to whoever started the run.
            runtime = Runtime(
                app=self.app,
                options=self._options.model_copy(
                    update={
                        "device_code_hook": self._on_device_code,
                        "connection_listener": self._set,
                    }
                ),
                provider=_provider_for(self.app),
            )
            self._error = None
            self._state = ConnectionState.CONNECTING
            started = threading.Event()
            self._thread = threading.Thread(
                target=self._main,
                args=(runtime, started),
                name=f"arkitekt-{self.app.identifier}",
                daemon=True,
            )
            self._thread.start()
            # So that a cancel right after start has a task to cancel.
            started.wait()

    def cancel(self, timeout: Optional[float] = 10.0) -> None:
        """End the run: a pending login, or the providing. From any thread.

        Returns once the run stopped, or after ``timeout`` seconds -- a task that
        does not let go of its thread can outlive that, and the state says so:
        it is ``STOPPED`` only when the run is.

        Args:
            timeout: How long to wait for the run to stop. ``None`` waits for it.
        """
        with self._guard:
            thread, loop, task = self._thread, self._loop, self._task
        if thread is None or loop is None or task is None or not thread.is_alive():
            return
        try:
            loop.call_soon_threadsafe(task.cancel)
        except RuntimeError:  # the loop closed in between: the run is over
            return
        if thread is not threading.current_thread():
            thread.join(timeout)

    def _main(self, runtime: Runtime[Ctx], started: threading.Event) -> None:
        loop = asyncio.new_event_loop()
        try:
            self._loop = loop
            self._task = loop.create_task(self._aserve(runtime))
            started.set()
            loop.run_until_complete(self._task)
        finally:
            started.set()
            loop.close()

    async def _aserve(self, runtime: Runtime[Ctx]) -> None:
        """The run, start to end. Never raises: how it ended is its state."""
        try:
            await self._set(ConnectionState.CONNECTING)
            async with runtime:
                await runtime.arun(self._context)  # type: ignore[arg-type]
        except asyncio.CancelledError:
            await self._set(ConnectionState.STOPPED)
        except Exception as e:
            logger.warning("The detached run of %r failed", self.app.identifier, exc_info=True)
            self._error = e
            await self._set(ConnectionState.FAILED)
        else:
            await self._set(ConnectionState.STOPPED)

    async def _set(self, state: ConnectionState) -> None:
        self._state = state
        listener = self._options.connection_listener
        if listener is None:
            return
        try:
            await listener(state)
        except Exception:
            logger.warning("The connection listener failed on %s", state.value, exc_info=True)

    async def _on_device_code(self, challenge: "DeviceCodeChallenge") -> None:
        hook = self._options.device_code_hook
        if hook is None:
            from arkitekt.app.terminal import login_prompt

            hook = login_prompt(opened_browser=not self._options.headless)
        # The hook first: a listener told of the pending login finds what the
        # hook kept of it.
        await hook(challenge)
        await self._set(ConnectionState.AWAITING_LOGIN)


@overload
def run_detached(
    app: App[None],
    *,
    context: None = None,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    connection_listener: Optional["ConnectionListener"] = None,
    task_listener: Optional["TaskListener"] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> DetachedRun[None]: ...
@overload
def run_detached(
    app: App[Ctx],
    *,
    context: Ctx,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    connection_listener: Optional["ConnectionListener"] = None,
    task_listener: Optional["TaskListener"] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> DetachedRun[Ctx]: ...


def run_detached(
    app: App[Any],
    *,
    context: Any | None = None,  # noqa: ANN401
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    skip_cache: bool = False,
    reauth: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    connection_listener: Optional["ConnectionListener"] = None,
    task_listener: Optional["TaskListener"] = None,
    allow_insecure_transport: bool = False,
    device_id: Optional[str] = None,
    mesh: Optional[Union[MeshOptions, MeshProxy, bool]] = None,
) -> DetachedRun[Any]:
    """Run ``app`` beside a program that has a life of its own. Returns at once.

    :func:`run` blocks until the app stops, which suits a script. A program that
    embeds an app -- one with its own window, its own server, its own threads --
    uses this instead of a thread of its own around :func:`run`: the run it gets
    back can be watched and cancelled from anywhere::

        async def on_state(state: ConnectionState) -> None:
            panel.show(state.value)

        async def on_code(challenge: DeviceCodeChallenge) -> None:
            panel.ask_to_open(challenge.verification_uri_complete, challenge.user_code)

        running = run_detached(
            app, context=setup, headless=True,
            device_code_hook=on_code, connection_listener=on_state,
        )
        ...
        running.cancel()          # on shutdown, or when the user disconnects
        running.start()           # and connects again

    The listeners and the hook are called on the run's own thread; what they do
    to the host's interface is theirs to hand over to it.

    Args:
        app: The app to provide.
        context: The app context, as for :func:`run`.
        connection_listener: Told every change of the run's :attr:`~DetachedRun.state`:
            ``CONNECTING``, ``AWAITING_LOGIN`` (after ``device_code_hook`` was
            called), ``REGISTERED``, ``DISCONNECTED`` (the link dropped and is
            being retried), ``FAILED`` and ``STOPPED``.

    Everything else is :func:`run`'s.

    Returns:
        The run, already started.

    Raises:
        AppContextError: If ``context`` is not what the app declared.
        RuntimeNotInstalledError: If the app offers something and no runtime is
            installed.
    """
    app.registry.require_app_context(context, whose=f"App {app.identifier!r}")
    running: DetachedRun[Any] = DetachedRun(
        app,
        context,
        ConnectionOptions(
            url=url,
            token=token,
            redeem_token=redeem_token,
            skip_cache=skip_cache,
            reauth=reauth,
            headless=headless,
            device_code_hook=device_code_hook,
            force=force,
            connection_listener=connection_listener,
            task_listener=task_listener,
            allow_insecure_transport=allow_insecure_transport,
            device_id=device_id,
            mesh=mesh,
        ),
    )
    running.start()
    return running


def has_stored_login(
    app: App[Any], *, url: Optional[str] = None, device_id: Optional[str] = None
) -> bool:
    """Whether a run of ``app`` would find a login on this machine and need no approval.

    Nothing connects: it reads the session saved for this app, at this version,
    on this server, and checks that it was approved for what the app declares now
    and has not aged out. The server has the last word when the run connects.

    Args:
        app: The app.
        url: The fakts server. Defaults to ``$FAKTS_URL``, then the public
            deployment.
        device_id: This device's identity. Defaults to the machine's id.
    """
    session = read_session(session_path(app.identifier, app.version, resolve_url(url)))
    if session is None:
        return False
    return session.is_for(run_manifest(app, device_id).hash()) and session.state() == "active"


async def _arevoke_stored(auth: "AuthFakt", server: str, allow_insecure_transport: bool) -> None:
    """Revoke a stored session at its server, where the server says how."""
    ssl_context = SSLContextModel().ssl_context
    endpoint = auth.revocation_endpoint
    if not endpoint:
        # A login from before servers said where to revoke: ask the server now.
        discovered = await WellKnownDiscovery(
            url=server, auto_protocols=["https", "http"], ssl_context=ssl_context
        ).adiscover()
        endpoint = discovered.revocation_endpoint
    if not endpoint:
        return
    await oauth2.arevoke(
        endpoint,
        client_id=auth.client_id,
        refresh_token=auth.refresh_token,
        ssl_context=ssl_context,
        allow_insecure_transport=allow_insecure_transport,
    )


def logout(
    app: App[Any], *, url: Optional[str] = None, allow_insecure_transport: bool = False
) -> bool:
    """Revoke ``app``'s login on its server and forget it on this machine.

    The next run needs a new approval. A server that advertises a revocation
    endpoint is told, so the session ends for every holder of a copy; one that
    advertises none (or cannot be reached) leaves the session forgotten here
    only. End a run still going on the session first -- it would write the
    session back when its token rotates.

    Args:
        app: The app.
        url: The fakts server. Defaults to ``$FAKTS_URL``, then the public
            deployment.
        allow_insecure_transport: Revoke over plain http at a server that is not
            on this machine.

    Returns:
        Whether there was a login to forget.
    """
    server = resolve_url(url)
    path = session_path(app.identifier, app.version, server)
    auth = read_credentials(path)
    if auth is not None and auth.refresh_token:
        # On a thread of its own: this may be called from inside a running loop.
        failure: List[BaseException] = []

        def revoke() -> None:
            try:
                asyncio.run(_arevoke_stored(auth, server, allow_insecure_transport))
            except Exception as e:  # noqa: BLE001 -- a logout must still forget the session
                failure.append(e)

        thread = threading.Thread(target=revoke, name="arkitekt-logout")
        thread.start()
        thread.join()
        if failure:
            logger.warning(
                "Could not revoke the login at %s (%s); it is forgotten here only.",
                server,
                failure[0],
            )
    return forget(path)


__all__ = [
    "DetachedRun",
    "Runtime",
    "alogin",
    "arun",
    "connect",
    "has_stored_login",
    "logout",
    "run",
    "run_detached",
    "run_manifest",
]
