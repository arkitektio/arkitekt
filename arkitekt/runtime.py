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
from collections.abc import AsyncIterator, Callable, Iterator, Mapping, Sequence
from contextlib import asynccontextmanager
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeAlias,
    TypeVar,
    cast,
    overload,
)

from arkitekt_spec.declare.agents.connection import ConnectionState
from arkitekt_spec.declare.provider import Provider
from arkitekt_spec.declare.service import Service
from fakts import Fakts, oauth2
from fakts.grants.remote.authorizers.device_code import (
    DeviceCodeChallenge,
    DeviceCodeHook,
)
from fakts.grants.remote.discovery.well_known import WellKnownDiscovery
from fakts.grants.remote.models import SSLContextModel
from fakts.mesh import MeshOptions, MeshProxy
from fakts.models import AliasPolicy
from koil import unkoil
from koil.bridge import unkoil_task
from koil.composition import KoiledModel
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from arkitekt.app.app import App, Ctx
from arkitekt.app.fakts import build_fakts, resolve_insecure_transport, resolve_url
from arkitekt.app.options import ConnectionOptions
from arkitekt.app.sessions import forget, read_credentials, read_session, session_path
from arkitekt.app.snapshot import RunSnapshot
from arkitekt.app.sources import DISCOVER, Source, resolve
from arkitekt.device_id import resolve_device_id

if TYPE_CHECKING:
    from arkitekt_runtime.agents.base import BaseAgent
    from arkitekt_spec.declare.agents.connection import ConnectionListener, TaskListener
    from fakts.models import ActiveFakts, AuthFakt, Manifest
    from koil import KoilFuture

    from arkitekt.checks import UnmetDependency


logger = logging.getLogger(__name__)

T = TypeVar("T")
#: The runtime ``async with`` enters: itself, as the subclass it is.
_RuntimeT = TypeVar("_RuntimeT", bound="Runtime[Any]")

#: An action of the app, as a caller names it: its name, the decorated function, or
#: the plain one.
_ActionRef: TypeAlias = "str | Callable[..., object]"


#: Where an offline run's services point: a host that can never resolve.
OFFLINE_HOST = "offline.invalid"


class LocalRun(BaseModel):
    """What makes a run local: nothing is registered, and its own actions are called in-process.

    Attributes:
        clients: Clients to use in place of the ones the app's services build. A
            service whose client class one of them is an instance of is not built.
        offline: Reach no server at all. A service that is not replaced then
            builds its real client against an address that does not exist: it is
            there to be handed out, and fails when something calls through it.
        context: The app context the run is started with.
    """

    clients: list[Any] = Field(default_factory=list)
    offline: bool = True
    context: Any | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


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
    snapshot: RunSnapshot | None = None
    fakts: Fakts | None = None
    clients: dict[str, Any] = Field(default_factory=dict)
    # ``Any``: an agent is an ``AgentLifecycle``, a Protocol with a data member,
    # which pydantic cannot validate against.
    agent: Any | None = None
    provider: Any | None = Field(default=None, exclude=True)
    local: LocalRun | None = Field(default=None, exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    _entered: list[Any] = PrivateAttr(default_factory=list)
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

    def get(self, cls: type[T]) -> T | None:
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

    def require(self, cls: type[T]) -> T:
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
        if self.local is not None:
            # The same snapshot a providing run takes, provider included: the app
            # is then whole (the structures its provider's package brings resolve)
            # and, connected, it is the manifest the saved session was made for --
            # a local call reuses the login of `run`, and does not replace it.
            # Only the agent differs: it is built here, not by the provider.
            device_id = (
                None
                if self.local.offline
                else resolve_device_id(self.options.device_id)
            )
            return self.app.snapshot(
                device_id=device_id, provider=_provider_for(self.app, required=False)
            )
        device_id = resolve_device_id(self.options.device_id)
        return self.app.snapshot(device_id=device_id, provider=self.provider)

    def _build_fakts(self, snapshot: RunSnapshot) -> Fakts:
        """The run's fakts: the deployment's, or for an offline run one that reaches nothing.

        Offline, every requirement resolves to an address that does not exist
        (``<key>.offline.invalid``). The services that were not replaced then
        build their real clients, so the app is whole and its structures bind;
        a client only fails when something actually calls through it.
        """
        if self.local is not None and self._stays_offline(snapshot):
            from fakts.testing import build_testing_fakts

            return build_testing_fakts(
                aliases={
                    requirement.key: f"http://{requirement.key}.{OFFLINE_HOST}"
                    for requirement in snapshot.manifest.requirements or []
                }
            )
        # Through the module, so the fakts stays replaceable (tests patch it).
        return build_fakts(snapshot.manifest, self.options)

    def _stays_offline(self, snapshot: RunSnapshot) -> bool:
        """Whether a local run reaches no server: asked to, or with nothing to reach.

        What a local run connects for is the services the app itself uses. The
        one its provider brings (rekuest's) serves an agent, and a local run's
        agent talks to nobody: an app using no service logs in to nothing.
        """
        assert self.local is not None
        if self.local.offline:
            return True
        own = self.app.registry.services
        return not any(
            service.needs_fakts and self._replacement_for(service) is None
            for name, service in snapshot.services.items()
            if name in own
        )

    def _replacement_for(self, service: "Service[Any]") -> object | None:
        """The client a local run was handed in place of the one ``service`` builds."""
        if self.local is None:
            return None
        return next(
            (c for c in self.local.clients if isinstance(c, service.returns)), None
        )

    def _needs_fakts(self, snapshot: RunSnapshot) -> bool:
        """Whether anything this run builds resolves through fakts."""
        if self.local is not None:
            return any(
                service.needs_fakts and self._replacement_for(service) is None
                for service in snapshot.services.values()
            )
        return any(service.needs_fakts for service in snapshot.services.values()) or (
            self.provider is not None and self.provider.needs_fakts
        )

    async def _build_clients(
        self, snapshot: RunSnapshot, fakts: Fakts | None
    ) -> dict[str, Any]:
        """Resolve each service's requirements and build its client.

        Runs after fakts is entered: a service is handed the *resolved* address of
        each thing it requires, which needs a loaded configuration. An unreachable
        required service therefore fails here, while the run is still connecting,
        rather than on the first call that happens to need it.
        """
        clients: dict[str, Any] = {}
        for name, builder in snapshot.services.items():
            # Each service takes only what its signature asks for; there is no
            # bag of parameters every builder has to know about.
            client = self._replacement_for(builder)
            if client is None:
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
        self, snapshot: RunSnapshot, fakts: Fakts | None
    ) -> "BaseAgent | None":
        """Build the agent from this run's provider, after the clients, and make it this run's."""
        if self.local is not None:
            agent = _local_agent(snapshot)
        else:
            provider = self.provider
            if provider is None:
                return None
            agent = await provider.build(fakts, snapshot.registry, self.clients)
        # Bound before entered: the agent reads `bound_app` while registering.
        agent.bound_app = self
        agent.force = self.options.force
        # Whoever started this process (e.g. the plugin engine) names itself here; the
        # agent states it on every Register, as a hint pickers narrow on.
        supervisor = resolve(
            self.options.supervisor,
            flag="supervisor",
            env=SUPERVISOR_ENV,
            default=lambda: None,
            parse=str,
        )
        if supervisor:
            try:
                agent.supervisor = supervisor
            except (AttributeError, ValueError):
                logger.debug("%r takes no supervisor", type(agent).__name__)
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

    async def __aenter__(self: _RuntimeT) -> _RuntimeT:
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
                self.fakts = self._build_fakts(snapshot)
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
            if self.local is not None:
                # A local run has nothing to wait for: it is started here, hooks
                # and states included, and stopped (shutdown hooks) on leaving.
                self._require_context(self.local.context)
                await self._require_agent().aconnect(context=self.local.context)
        except BaseException as e:
            await self._exit_entered(type(e), e, e.__traceback__)
            raise
        return self

    async def _exit_entered(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        while self._entered:
            part = self._entered.pop()
            try:
                await part.__aexit__(exc_type, exc_value, traceback)
            except Exception:
                logger.exception("Failed to close %r while leaving the runtime", part)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
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

    def _require_agent(self) -> "BaseAgent":
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

    def _require_context(self, context: object) -> None:
        self.app.registry.require_app_context(
            context, whose=f"App {self.app.identifier!r}"
        )

    @overload
    async def arun(self: "Runtime[None]", context: None = None) -> None: ...
    @overload
    async def arun(self, context: Ctx) -> None: ...

    async def arun(self, context: Ctx | None = None) -> None:
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

    async def _aprovide(self, context: Ctx | None) -> None:
        """Provide the app's offerings with ``context``, already checked by the caller."""
        await self._require_agent().aprovide(context=context)

    @overload
    async def astart(
        self: "Runtime[None]", context: None = None, *, timeout: float | None = None
    ) -> None: ...
    @overload
    async def astart(self, context: Ctx, *, timeout: float | None = None) -> None: ...

    async def astart(
        self, context: Ctx | None = None, *, timeout: float | None = None
    ) -> None:
        """Start the app and register its agent: the first half of :meth:`arun`.

        Returns once the server has acknowledged the agent, so what follows may
        rely on the app being there. Nothing is served until :meth:`aloop`::

            async with connect(app, provide=True) as rt:
                await rt.astart(timeout=30)
                serving = asyncio.create_task(rt.aloop())
                ...

        Args:
            context: The app context, as for :meth:`arun`.
            timeout: How long the start (startup hooks and registration) may
                take, in seconds. Unbounded when ``None``.

        Raises:
            AppContextError: If ``context`` is not what the app declared.
            LookupError: If the app offers nothing.
            TimeoutError: If the start takes longer than ``timeout``.
        """
        self._require_context(context)
        await self._require_agent().aconnect(context=context, timeout=timeout)

    async def aloop(self) -> None:
        """Serve the started app until stopped: the second half of :meth:`arun`.

        Cancelling it shuts the agent down (shutdown hooks included), so cancel
        it and wait for it before leaving the runtime.

        Raises:
            LookupError: If the app offers nothing.
        """
        await self._require_agent().aloop()

    @overload
    def run(self: "Runtime[None]", context: None = None) -> None: ...
    @overload
    def run(self, context: Ctx) -> None: ...

    def run(self, context: Ctx | None = None) -> None:
        """Run the app until stopped: provide its offerings. The runtime must be entered.

        Raises:
            AppContextError: If ``context`` is not what the app declared.
            LookupError: If the app offers nothing.
        """
        self._require_context(context)
        unkoil(self._aprovide, context)

    @overload
    def run_detached(
        self: "Runtime[None]", context: None = None
    ) -> "KoilFuture[None]": ...
    @overload
    def run_detached(self, context: Ctx) -> "KoilFuture[None]": ...

    def run_detached(self, context: Ctx | None = None) -> "KoilFuture[None]":
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

    # ------------------------------------------------------------------ #
    # Calling in-process                                                 #
    # ------------------------------------------------------------------ #

    def _local_call(self, action: _ActionRef) -> "tuple[BaseAgent, str]":
        """The agent of this local run and the interface ``action`` names on it."""
        agent = self.agent
        if self.local is None or agent is None:
            raise LookupError(
                "Only a local run calls its own actions in-process: "
                "`connect_local(app)`, or `local_app(app)` in a test."
            )
        return agent, _interface_of(agent, action)

    async def acall_local(self, action: _ActionRef, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401 -- what the app's action returns
        """Call one of the app's own actions in-process and return its result.

        The call goes through the app's agent, as an assignment from a server
        does: the arguments cross the action's ports, the action is handed the
        run's clients, its task and its states, and the result crosses the ports
        back. Only the server is missing.

        Args:
            action: The action: the decorated function, or its name.
            *args: Its arguments, as Python values.
            **kwargs: Ditto, by keyword.

        Returns:
            What the action returned; of a generator, what it yielded last.

        Raises:
            LookupError: If this is not a local run.
            KeyError: If the app has no such action.
            LocalCallError: If the action fails or raises.
        """
        from arkitekt_runtime.local import acall_local

        agent, interface = self._local_call(action)
        return await acall_local(agent, interface, *args, **kwargs)

    async def aiterate_local(
        self,
        action: _ActionRef,
        *args: Any,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        """Call one of the app's own actions in-process and yield each of its results.

        See :meth:`acall_local`.
        """
        from arkitekt_runtime.local import aiterate_local

        agent, interface = self._local_call(action)
        async for result in aiterate_local(agent, interface, *args, **kwargs):
            yield result

    async def aiterate_local_raw(
        self,
        action: _ActionRef,
        args: dict[str, Any],
    ) -> AsyncIterator[Any]:
        """Call one of the app's own actions with arguments as they travel, and yield
        each result as it would travel back: what a server sends and receives.

        See :meth:`acall_local`; this is its wire-level form, for a caller that has
        JSON rather than Python values (the command line).
        """
        from arkitekt_runtime.local import aiterate_local_raw

        agent, interface = self._local_call(action)
        async for returns in aiterate_local_raw(agent, interface, args):
            yield returns

    def call_local(self, action: _ActionRef, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401 -- what the app's action returns
        """Call one of the app's own actions in-process (see :meth:`acall_local`)."""
        return unkoil(self.acall_local, action, *args, **kwargs)


def _interface_of(agent: "BaseAgent", action: _ActionRef) -> str:
    """The interface ``action`` names on ``agent``: its name, the decorated function, or the plain one.

    Raises:
        KeyError: If the app has no such action.
    """
    if isinstance(action, str):
        return action
    interface = getattr(action, "interface", None)
    if isinstance(interface, str):
        return interface
    # The plain function, as a module that kept it from before decorating has it.
    declared = agent.app_registry.declared_implementations
    for name, implementation in declared.items():
        if implementation.function is action:
            return name
    raise KeyError(
        f"{getattr(action, '__name__', action)!r} is not an action of this app. "
        f"It has: {', '.join(sorted(declared)) or 'none'}."
    )


def _local_agent(snapshot: RunSnapshot) -> "BaseAgent":
    """The agent of a local run: the runtime's own, on a transport that goes nowhere."""
    try:
        from arkitekt_runtime.local import local_agent
    except ImportError as e:
        raise RuntimeNotInstalledError(
            "Calling an app's actions in-process needs the runtime, which is not "
            "installed: pip install 'arkitekt[rekuest]'."
        ) from e
    return local_agent(
        snapshot.registry,
        name=f"{snapshot.manifest.identifier}:{snapshot.manifest.version}",
    )


def connect_local(
    app: App[Ctx],
    *,
    clients: Sequence[Any] = (),
    context: Ctx | None = None,
    offline: bool = True,
    url: str | Source = DISCOVER,
    token: str | Source | None = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    task_listener: "TaskListener | None" = None,
    allow_insecure_transport: bool | Source = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
) -> Runtime[Ctx]:
    """Make a runtime that runs ``app`` for itself: nothing is registered or served.

    For trying an action and for tests::

        with connect_local(app) as rt:
            assert rt.call_local(add, 1, 2) == 3

    Entering it starts the app as a run does (startup hooks, states, background
    work); leaving it stops it. In between :meth:`Runtime.call_local` calls the
    app's actions through its agent, with no server in between.

    Args:
        app: The app to run.
        clients: Clients to use in place of the ones the app's services build,
            matched by class: a ``Mikro`` in ``clients`` is what an action
            taking ``mikro: Mikro`` is handed. It is entered and left with
            the run, so it must not be entered already.
        context: The app context, for an app that declares one.
        offline: Reach no server. Off, the services that are not replaced are
            built against the deployment, with a login as for :func:`connect`
            (which the remaining arguments describe).

    Returns:
        The runtime, not yet entered.
    """
    return Runtime(
        app=app,
        options=ConnectionOptions(
            url=url,
            token=token,
            mandate_key=mandate_key,
            skip_cache=skip_cache,
            reauth=reauth,
            headless=headless,
            device_code_hook=device_code_hook,
            task_listener=task_listener,
            allow_insecure_transport=allow_insecure_transport,
            mesh=mesh,
            alias_policy=alias_policy,
        ),
        local=LocalRun(clients=list(clients), offline=offline, context=context),
    )


#: What ``run()`` says when an app offers something and no runtime is installed.
NO_RUNTIME_HINT = (
    "This app offers actions, states or bloks, and running it needs a runtime that is "
    "not installed. Install rekuest (pip install 'arkitekt[rekuest]') to run it in "
    "distributed mode, or serve it with `serve(app, fastapi_app)` (arkitekt[serve])."
)


class RuntimeNotInstalledError(ImportError):
    """``run()`` was asked to serve an app, and no runtime (rekuest) is installed."""


def _provider_for(app: App[Any], *, required: bool = True) -> Provider[Any] | None:
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


SUPERVISOR_ENV = "ARKITEKT_SUPERVISOR"
"""Set by the app that started this process to control its lifecycle (e.g. ``plugin_engine``).

The run's agent sends it with every ``Register``: it becomes the ``@rekuest/supervisor``
descriptor of the agent, which that supervisor's actions narrow their pickers on."""


def connect(
    app: App[Ctx],
    *,
    provide: bool = False,
    url: str | Source = DISCOVER,
    token: str | Source | None = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    force: bool = False,
    connection_listener: "ConnectionListener | None" = None,
    task_listener: "TaskListener | None" = None,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
    supervisor: str | Source | None = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
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
        url: The fakts server, or where to find it (a source, see
            :mod:`arkitekt.app.sources`). Defaults to ``"discover"``: ``--url``,
            ``$FAKTS_URL``, then the public deployment.
        token: A previously issued credential, ``client_id:refresh_token``.
            Defaults to ``"discover"``: ``--token``, then ``$FAKTS_TOKEN``;
            ``None`` uses none.
        mandate_key: A mandate key to log the app in with. Defaults to
            ``"discover"``: ``--mandate-key``, then ``$FAKTS_MANDATE_KEY``;
            ``None`` uses none.
        skip_cache: Neither read nor write the fakts cache: log in, and keep the
            session in memory only.
        reauth: Log in again even when a session is cached, and cache the new
            one. Defaults to ``"discover"``: ``--reauth``, then
            ``$ARKITEKT_REAUTH``, else off.
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
            machine. Off, such a server is refused. Defaults to ``"discover"``:
            ``--allow-insecure-transport``, then ``$FAKTS_ALLOW_INSECURE_TRANSPORT``,
            else off.
        device_id: This device's identity. Defaults to ``"discover"``:
            ``--device-id``, then ``$ARKITEKT_DEVICE_ID``, then the machine's id;
            ``None`` states none.
        supervisor: The app that controls this process's lifecycle (e.g.
            ``plugin_engine``), stated by its agent on every Register. Defaults to
            ``"discover"``: ``--supervisor``, then ``$ARKITEKT_SUPERVISOR``;
            ``None`` states none.
        alias_policy: This run's own say over which aliases it uses, on top of the
            hub owner's ranking (``fakts.AliasPolicy``); ``None``: ``$FAKTS_ALIAS_*``.
        mesh: How to reach services only on the deployment's mesh:
            ``MeshOptions()`` or ``True`` runs a node in this process,
            ``MeshProxy(url=...)`` goes through a running proxy, ``False`` is off.
            ``None`` too. Defaults to ``"discover"``: ``--mesh``, then
            ``$ARKITEKT_MESH_PROXY`` / ``$ARKITEKT_MESH``, else the mesh when it is
            available (see :func:`arkitekt.app.fakts.mesh_from_env`).

    Returns:
        The runtime, not yet entered.
    """
    return Runtime(
        app=app,
        options=ConnectionOptions(
            url=url,
            token=token,
            mandate_key=mandate_key,
            skip_cache=skip_cache,
            reauth=reauth,
            headless=headless,
            device_code_hook=device_code_hook,
            force=force,
            connection_listener=connection_listener,
            task_listener=task_listener,
            allow_insecure_transport=allow_insecure_transport,
            device_id=device_id,
            supervisor=supervisor,
            mesh=mesh,
            alias_policy=alias_policy,
        ),
        provider=_provider_for(app) if provide else None,
    )


@overload
def run(
    app: App[None],
    *,
    context: None = None,
    url: str | Source = DISCOVER,
    token: str | Source | None = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    force: bool = False,
    connection_listener: "ConnectionListener | None" = None,
    task_listener: "TaskListener | None" = None,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
    supervisor: str | Source | None = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
) -> None: ...
@overload
def run(
    app: App[Ctx],
    *,
    context: Ctx,
    url: str | Source = DISCOVER,
    token: str | Source | None = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    force: bool = False,
    connection_listener: "ConnectionListener | None" = None,
    task_listener: "TaskListener | None" = None,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
    supervisor: str | Source | None = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
) -> None: ...


def run(
    app: App[Any],
    *,
    context: object = None,
    url: str | Source = DISCOVER,
    token: str | Source | None = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    force: bool = False,
    connection_listener: "ConnectionListener | None" = None,
    task_listener: "TaskListener | None" = None,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
    supervisor: str | Source | None = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
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
        url: The fakts server, or where to find it (a source, see
            :mod:`arkitekt.app.sources`). Defaults to ``"discover"``: ``--url``,
            ``$FAKTS_URL``, then the public deployment.
        token: A previously issued credential, ``client_id:refresh_token``.
            Defaults to ``"discover"``: ``--token``, then ``$FAKTS_TOKEN``;
            ``None`` uses none.
        mandate_key: A mandate key to log the app in with. Defaults to
            ``"discover"``: ``--mandate-key``, then ``$FAKTS_MANDATE_KEY``;
            ``None`` uses none.
        skip_cache: Neither read nor write the fakts cache: log in, and keep the
            session in memory only.
        reauth: Log in again even when a session is cached, and cache the new
            one. Defaults to ``"discover"``: ``--reauth``, then
            ``$ARKITEKT_REAUTH``, else off.
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
            machine. Off, such a server is refused. Defaults to ``"discover"``:
            ``--allow-insecure-transport``, then ``$FAKTS_ALLOW_INSECURE_TRANSPORT``,
            else off.
        device_id: This device's identity. Defaults to ``"discover"``:
            ``--device-id``, then ``$ARKITEKT_DEVICE_ID``, then the machine's id;
            ``None`` states none.
        supervisor: The app that controls this process's lifecycle (e.g.
            ``plugin_engine``), stated by its agent on every Register. Defaults to
            ``"discover"``: ``--supervisor``, then ``$ARKITEKT_SUPERVISOR``;
            ``None`` states none.
        alias_policy: This run's own say over which aliases it uses, on top of the
            hub owner's ranking (``fakts.AliasPolicy``); ``None``: ``$FAKTS_ALIAS_*``.
        mesh: How to reach services only on the deployment's mesh:
            ``MeshOptions()`` or ``True`` runs a node in this process,
            ``MeshProxy(url=...)`` goes through a running proxy, ``False`` is off.
            ``None`` too. Defaults to ``"discover"``: ``--mesh``, then
            ``$ARKITEKT_MESH_PROXY`` / ``$ARKITEKT_MESH``, else the mesh when it is
            available (see :func:`arkitekt.app.fakts.mesh_from_env`).

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
        mandate_key=mandate_key,
        skip_cache=skip_cache,
        reauth=reauth,
        headless=headless,
        device_code_hook=device_code_hook,
        force=force,
        connection_listener=connection_listener,
        task_listener=task_listener,
        allow_insecure_transport=allow_insecure_transport,
        device_id=device_id,
        supervisor=supervisor,
        mesh=mesh,
        alias_policy=alias_policy,
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
    url: str | Source = DISCOVER,
    token: str | Source | None = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    force: bool = False,
    connection_listener: "ConnectionListener | None" = None,
    task_listener: "TaskListener | None" = None,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
    supervisor: str | Source | None = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
) -> None: ...
@overload
async def arun(
    app: App[Ctx],
    *,
    context: Ctx,
    url: str | Source = DISCOVER,
    token: str | Source | None = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    force: bool = False,
    connection_listener: "ConnectionListener | None" = None,
    task_listener: "TaskListener | None" = None,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
    supervisor: str | Source | None = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
) -> None: ...


async def arun(
    app: App[Any],
    *,
    context: object = None,
    url: str | Source = DISCOVER,
    token: str | Source | None = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    force: bool = False,
    connection_listener: "ConnectionListener | None" = None,
    task_listener: "TaskListener | None" = None,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
    supervisor: str | Source | None = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
) -> None:
    """Connect ``app`` and provide its actions until stopped, asynchronously.

    Args:
        app: The app to provide.
        context: The app context, as for :func:`run`.
        url: The fakts server, or where to find it (a source, see
            :mod:`arkitekt.app.sources`). Defaults to ``"discover"``: ``--url``,
            ``$FAKTS_URL``, then the public deployment.
        token: A previously issued credential, ``client_id:refresh_token``.
            Defaults to ``"discover"``: ``--token``, then ``$FAKTS_TOKEN``;
            ``None`` uses none.
        mandate_key: A mandate key to log the app in with. Defaults to
            ``"discover"``: ``--mandate-key``, then ``$FAKTS_MANDATE_KEY``;
            ``None`` uses none.
        skip_cache: Neither read nor write the fakts cache: log in, and keep the
            session in memory only.
        reauth: Log in again even when a session is cached, and cache the new
            one. Defaults to ``"discover"``: ``--reauth``, then
            ``$ARKITEKT_REAUTH``, else off.
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
            machine. Off, such a server is refused. Defaults to ``"discover"``:
            ``--allow-insecure-transport``, then ``$FAKTS_ALLOW_INSECURE_TRANSPORT``,
            else off.
        device_id: This device's identity. Defaults to ``"discover"``:
            ``--device-id``, then ``$ARKITEKT_DEVICE_ID``, then the machine's id;
            ``None`` states none.
        supervisor: The app that controls this process's lifecycle (e.g.
            ``plugin_engine``), stated by its agent on every Register. Defaults to
            ``"discover"``: ``--supervisor``, then ``$ARKITEKT_SUPERVISOR``;
            ``None`` states none.
        alias_policy: This run's own say over which aliases it uses, on top of the
            hub owner's ranking (``fakts.AliasPolicy``); ``None``: ``$FAKTS_ALIAS_*``.
        mesh: How to reach services only on the deployment's mesh:
            ``MeshOptions()`` or ``True`` runs a node in this process,
            ``MeshProxy(url=...)`` goes through a running proxy, ``False`` is off.
            ``None`` too. Defaults to ``"discover"``: ``--mesh``, then
            ``$ARKITEKT_MESH_PROXY`` / ``$ARKITEKT_MESH``, else the mesh when it is
            available (see :func:`arkitekt.app.fakts.mesh_from_env`).

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
        mandate_key=mandate_key,
        skip_cache=skip_cache,
        reauth=reauth,
        headless=headless,
        device_code_hook=device_code_hook,
        force=force,
        connection_listener=connection_listener,
        task_listener=task_listener,
        allow_insecure_transport=allow_insecure_transport,
        device_id=device_id,
        supervisor=supervisor,
        mesh=mesh,
        alias_policy=alias_policy,
    )
    async with runtime:
        await runtime.arun(context=context)


def _labelled_login_prompt(identifier: str, headless: bool) -> DeviceCodeHook:
    """The terminal login prompt, saying which app asks: several apps log in at once."""
    from rich.console import Console
    from rich.markup import escape

    from arkitekt.app.terminal import login_prompt

    prompt = login_prompt(opened_browser=not headless)

    async def hook(challenge: DeviceCodeChallenge) -> None:
        Console().print(
            f"[bold]{escape(identifier)}[/bold] asks to log in", highlight=False
        )
        await prompt(challenge)

    return hook


class RunningApps(Mapping[str, "Runtime[Any]"]):
    """The apps of a :func:`providing` block: their runtimes, by app.

    ::

        async with providing(upper_app, reverse_app) as running:
            upper = running[upper_app].require(RekuestCaller)
            await running.wait()

    It is a mapping by app identifier (``running["upper"]``, iteration, ``len``);
    looking a runtime up by the app itself keeps the type of its context.
    """

    def __init__(
        self,
        runtimes: Mapping[str, "Runtime[Any]"],
        serving: Sequence["asyncio.Task[None]"],
    ) -> None:
        """Hold the started runtimes and the tasks serving them."""
        self._runtimes = runtimes
        self._serving = serving

    @overload
    def __getitem__(self, app: App[Ctx]) -> "Runtime[Ctx]": ...
    @overload
    def __getitem__(self, app: str) -> "Runtime[Any]": ...

    def __getitem__(self, app: "App[Any] | str") -> "Runtime[Any]":
        """The runtime of an app: by the app, or by its identifier.

        Raises:
            KeyError: If the app is not one of those provided.
        """
        if isinstance(app, str):
            return self._runtimes[app]
        runtime = self._runtimes.get(app.identifier)
        if runtime is None or runtime.app is not app:
            raise KeyError(
                f"App {app.identifier!r} is not one of the apps provided here: {sorted(self._runtimes)}."
            )
        return runtime

    def __iter__(self) -> Iterator[str]:
        """The identifiers of the apps."""
        return iter(self._runtimes)

    def __len__(self) -> int:
        """How many apps are provided."""
        return len(self._runtimes)

    async def check(self) -> "list[UnmetDependency]":
        """Ask the server whether every dependency of these apps would bind now.

        The live counterpart of ``check=True``: the server resolves each action's
        dependencies as an assign would, among every agent registered with it, so
        one served by an app that is not run here is checked too::

            async with providing(lab_app) as running:
                for unmet in await running.check():
                    print(unmet)

        Returns:
            What an assign would be refused for; empty when all of them would go
            through. See :func:`arkitekt.checks.acheck_running`.
        """
        from arkitekt.checks import acheck_running

        return await acheck_running(self._runtimes.values())

    async def wait(self) -> None:
        """Serve until stopped: return once every app has stopped.

        An app that fails does not wait for the rest: it ends this wait, the
        block and the other apps, and its error is raised from the block.
        """
        await asyncio.wait(self._serving)


@asynccontextmanager
async def providing(
    *apps: App[Any],
    contexts: Mapping[str, Any] | None = None,
    timeout: float | None = None,
    check: bool = False,
    url: str | Source = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    force: bool = False,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
) -> AsyncIterator[RunningApps]:
    """Several apps, connected, registered and provided for as long as the block runs.

    Every app is its own agent with its own login, in its own task. The block is
    entered once all of them are registered, with their runtimes by app,
    and leaving it stops them::

        async with providing(upper_app, reverse_app, pipeline_app) as running:
            rekuest = running[pipeline_app].require(RekuestCaller)
            await rekuest.acall(process, text="hello")
            await running.wait()  # go on serving until stopped

    They connect and register at once, in no order: what an app depends on is
    bound when one of its tasks is assigned, not when it registers. An app that
    fails, before or while the block runs, stops the others and the block.

    For apps that need no identity of their own, one merged app
    (:func:`arkitekt.merge`) is one agent and one login instead.

    A token (``--token``, ``$FAKTS_TOKEN``) is one app's credential, so none is
    read here: each app uses its saved login, the mandate key, or asks.

    Args:
        *apps: The apps to provide. Their identifiers must differ: the
            identifier names an app's saved login.
        contexts: The app context of each app that declares one, by the app's
            identifier (see :func:`run`).
        timeout: How long each app's start (startup hooks and registration) may
            take once it is logged in, in seconds. Unbounded when ``None``.
        check: Compare what the apps demand of each other first
            (:func:`arkitekt.check_apps`) and refuse to start when one demands
            what another does not offer. A dependency on an app that is not
            among ``apps`` is not checked. Off by default.
        url: The fakts server, or where to find it, for all of them (see
            :func:`run`).
        mandate_key: A mandate key to log each app in with (see :func:`run`).
        skip_cache: Neither read nor write the fakts cache (see :func:`run`).
        reauth: Log in again even when a session is cached (see :func:`run`).
        headless: Print the device-code prompts instead of opening a browser.
        device_code_hook: Called with each login to approve, instead of the
            terminal prompt. Without one, each prompt names the app it is for.
        force: Take over an existing agent connection of each app.
        allow_insecure_transport: Talk plain http to a server that is not on
            this machine (see :func:`run`).
        device_id: This device's identity (see :func:`run`).
        alias_policy: This run's own say over which aliases it uses, on top of the
            hub owner's ranking (``fakts.AliasPolicy``); ``None``: ``$FAKTS_ALIAS_*``.
        mesh: How to reach services only on the deployment's mesh (see
            :func:`run`).

    Yields:
        The running apps: their runtimes by app, and ``wait()``.

    Raises:
        ValueError: If no app is given, two apps share an identifier, or
            ``contexts`` names an app that is not given. Raised before anything
            connects or logs in.
        AppContextError: If a context is not what its app declared. Raised
            before anything connects or logs in.
        DependencyCheckError: With ``check``, if an app demands what another
            does not offer. Raised before anything connects or logs in.
        LookupError: If an app offers nothing.
        TimeoutError: If an app does not start within ``timeout``.
    """
    if not apps:
        raise ValueError("No app to run: at least one is needed.")
    identifiers = [app.identifier for app in apps]
    twice = sorted({i for i in identifiers if identifiers.count(i) > 1})
    if twice:
        raise ValueError(
            f"These apps share an identifier: {twice}. An identifier names an app's "
            "saved login, so every app run together needs its own."
        )
    contexts = contexts or {}
    unknown = sorted(set(contexts) - set(identifiers))
    if unknown:
        raise ValueError(
            f"`contexts` names apps that are not run: {unknown}. Running: {identifiers}."
        )
    for app in apps:
        app.registry.require_app_context(
            contexts.get(app.identifier), whose=f"App {app.identifier!r}"
        )
    if check:
        from arkitekt.checks import DependencyCheckError, check_apps

        unmet = [finding for finding in check_apps(*apps) if finding.level == "error"]
        if unmet:
            raise DependencyCheckError(unmet)

    runtimes: dict[str, Runtime[Any]] = {}
    started = {identifier: asyncio.Event() for identifier in identifiers}

    async def provide(app: App[Any]) -> None:
        # One task enters, starts, serves and leaves the runtime: what a run
        # enters (cancel scopes, timeouts) is left in the task that entered it.
        identifier = app.identifier
        hook = device_code_hook
        if hook is None and len(apps) > 1:
            hook = _labelled_login_prompt(identifier, headless)
        runtime = connect(
            app,
            provide=True,
            url=url,
            token=None,
            mandate_key=mandate_key,
            skip_cache=skip_cache,
            reauth=reauth,
            headless=headless,
            device_code_hook=hook,
            force=force,
            allow_insecure_transport=allow_insecure_transport,
            device_id=device_id,
            mesh=mesh,
            alias_policy=alias_policy,
        )
        async with runtime:
            await runtime.astart(contexts.get(identifier), timeout=timeout)
            runtimes[identifier] = runtime
            started[identifier].set()
            await runtime.aloop()

    try:
        async with asyncio.TaskGroup() as group:
            serving = [
                group.create_task(provide(app), name=app.identifier) for app in apps
            ]
            # An app failing to start cancels this wait, and the others, through the group.
            await asyncio.gather(*(event.wait() for event in started.values()))
            try:
                yield RunningApps(runtimes, serving)
            finally:
                # Cancelling a served app shuts its agent down and leaves its runtime.
                for task in serving:
                    task.cancel()
    except BaseExceptionGroup as errors:
        # One thing went wrong (an app, or the block): raise that, not a group of one.
        if len(errors.exceptions) == 1:
            raise errors.exceptions[0] from None
        raise


async def arun_all(
    *apps: App[Any],
    contexts: Mapping[str, Any] | None = None,
    timeout: float | None = None,
    check: bool = False,
    url: str | Source = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    force: bool = False,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
) -> None:
    """Connect several apps and provide each until stopped, in one process.

    :func:`providing`, held open until the apps stop: each app is its own agent
    with its own login, and one of them failing stops the others.

    Args:
        *apps: The apps to provide, each under its own identifier.
        contexts: The app context of each app that declares one, by identifier.
        timeout: How long each app's start may take once it is logged in, in
            seconds. Unbounded when ``None``.
        check: Check the apps against each other first, as for :func:`providing`.
        url: The fakts server, or where to find it, for all of them (see
            :func:`run`).
        mandate_key: A mandate key to log each app in with (see :func:`run`).
        skip_cache: Neither read nor write the fakts cache (see :func:`run`).
        reauth: Log in again even when a session is cached (see :func:`run`).
        headless: Print the device-code prompts instead of opening a browser.
        device_code_hook: Called with each login to approve, instead of the
            terminal prompt. Without one, each prompt names the app it is for.
        force: Take over an existing agent connection of each app.
        allow_insecure_transport: Talk plain http to a server that is not on
            this machine (see :func:`run`).
        device_id: This device's identity (see :func:`run`).
        alias_policy: This run's own say over which aliases it uses, on top of the
            hub owner's ranking (``fakts.AliasPolicy``); ``None``: ``$FAKTS_ALIAS_*``.
        mesh: How to reach services only on the deployment's mesh (see
            :func:`run`).

    Raises:
        ValueError: As for :func:`providing`.
        AppContextError: As for :func:`providing`.
        LookupError: If an app offers nothing.
        TimeoutError: If an app does not start within ``timeout``.
    """
    async with providing(
        *apps,
        contexts=contexts,
        timeout=timeout,
        check=check,
        url=url,
        mandate_key=mandate_key,
        skip_cache=skip_cache,
        reauth=reauth,
        headless=headless,
        device_code_hook=device_code_hook,
        force=force,
        allow_insecure_transport=allow_insecure_transport,
        device_id=device_id,
        mesh=mesh,
        alias_policy=alias_policy,
    ) as running:
        await running.wait()


def run_all(
    *apps: App[Any],
    contexts: Mapping[str, Any] | None = None,
    timeout: float | None = None,
    check: bool = False,
    url: str | Source = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    force: bool = False,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
) -> None:
    """Connect several apps and provide each until stopped: :func:`arun_all`, blocking.

    ::

        if __name__ == "__main__":
            run_all(upper_app, reverse_app, pipeline_app)

    Args:
        *apps: The apps to provide, each under its own identifier.
        contexts: The app context of each app that declares one, by identifier.
        timeout: How long each app's start may take once it is logged in, in
            seconds. Unbounded when ``None``.
        check: Check the apps against each other first, as for :func:`providing`.
        url: The fakts server, or where to find it, for all of them (see
            :func:`run`).
        mandate_key: A mandate key to log each app in with (see :func:`run`).
        skip_cache: Neither read nor write the fakts cache (see :func:`run`).
        reauth: Log in again even when a session is cached (see :func:`run`).
        headless: Print the device-code prompts instead of opening a browser.
        device_code_hook: Called with each login to approve, instead of the
            terminal prompt. Without one, each prompt names the app it is for.
        force: Take over an existing agent connection of each app.
        allow_insecure_transport: Talk plain http to a server that is not on
            this machine (see :func:`run`).
        device_id: This device's identity (see :func:`run`).
        alias_policy: This run's own say over which aliases it uses, on top of the
            hub owner's ranking (``fakts.AliasPolicy``); ``None``: ``$FAKTS_ALIAS_*``.
        mesh: How to reach services only on the deployment's mesh (see
            :func:`run`).

    Raises:
        ValueError: As for :func:`providing`.
        AppContextError: As for :func:`providing`.
        LookupError: If an app offers nothing.
        TimeoutError: If an app does not start within ``timeout``.
    """
    asyncio.run(
        arun_all(
            *apps,
            contexts=contexts,
            timeout=timeout,
            check=check,
            url=url,
            mandate_key=mandate_key,
            skip_cache=skip_cache,
            reauth=reauth,
            headless=headless,
            device_code_hook=device_code_hook,
            force=force,
            allow_insecure_transport=allow_insecure_transport,
            device_id=device_id,
            mesh=mesh,
            alias_policy=alias_policy,
        )
    )


def run_manifest(
    app: App[Any], device_id: str | Source | None = DISCOVER
) -> "Manifest":
    """The manifest a run of ``app`` sends: what the server is asked to approve.

    A session is saved for exactly this manifest: an app declared differently
    (another scope, another service, another device) logs in again. It is the
    providing run's, so it carries what the app's provider requires too.

    Args:
        app: The app.
        device_id: This device's identity. Defaults to ``"discover"``:
            ``--device-id``, then ``$ARKITEKT_DEVICE_ID``, then the machine's id;
            ``None`` states none.

    Returns:
        The manifest.
    """
    return connect(app, provide=True, device_id=device_id)._prepare().manifest


async def alogin(
    app: App[Any],
    *,
    url: str | Source = DISCOVER,
    token: str | Source | None = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
) -> "ActiveFakts":
    """Log ``app`` in and cache the session, without connecting anything else.

    What a run does first, on its own: no client is built and no agent, so a
    service that is down does not stand in the way of logging in. It logs in as
    the run would -- with the manifest the run sends, its provider's requirements
    included -- so the session saved is the one the run finds.

    Args:
        app: The app to log in.
        url: The fakts server, or where to find it (a source, see
            :mod:`arkitekt.app.sources`). Defaults to ``"discover"``: ``--url``,
            ``$FAKTS_URL``, then the public deployment.
        token: A previously issued credential, ``client_id:refresh_token``.
            Defaults to ``"discover"``: ``--token``, then ``$FAKTS_TOKEN``;
            ``None`` uses none.
        mandate_key: A mandate key to log the app in with. Defaults to
            ``"discover"``: ``--mandate-key``, then ``$FAKTS_MANDATE_KEY``;
            ``None`` uses none.
        skip_cache: Neither read nor write the fakts cache.
        reauth: Log in again even when a session is cached, and cache the new
            one. Defaults to ``"discover"``: ``--reauth``, then
            ``$ARKITEKT_REAUTH``, else off.
        headless: Print the device-code prompt instead of opening a browser.
        device_code_hook: Called with the login to approve -- a
            :class:`~arkitekt.DeviceCodeChallenge` carrying the code and the link --
            instead of the terminal prompt. With ``headless`` nothing is printed
            or opened: showing the login is the hook's.
        allow_insecure_transport: Talk plain http to a server that is not on this
            machine. Off, such a server is refused. Defaults to ``"discover"``:
            ``--allow-insecure-transport``, then ``$FAKTS_ALLOW_INSECURE_TRANSPORT``,
            else off.
        device_id: This device's identity. Defaults to ``"discover"``:
            ``--device-id``, then ``$ARKITEKT_DEVICE_ID``, then the machine's id;
            ``None`` states none.

    Returns:
        The session the app is logged in with.
    """
    options = ConnectionOptions(
        url=url,
        token=token,
        mandate_key=mandate_key,
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
        context: Ctx | None,
        options: ConnectionOptions,
    ) -> None:
        self.app = app
        self._context = context
        self._options = options
        self._state = ConnectionState.STOPPED
        self._error: BaseException | None = None
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task[None] | None = None
        self._guard = threading.Lock()

    @property
    def state(self) -> ConnectionState:
        """Where the run stands. ``connection_listener`` is told every change of it."""
        return self._state

    @property
    def error(self) -> BaseException | None:
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
            ended = self._state in (ConnectionState.FAILED, ConnectionState.STOPPED)
            if (
                ended
                and self._thread is not None
                and self._thread is not threading.current_thread()
            ):
                # It says it ended a moment before its thread is through tearing down.
                self._thread.join(timeout=5)
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

    def cancel(self, timeout: float | None = 10.0) -> None:
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
                await runtime.arun(self._context)  # pyright: ignore[reportArgumentType]
        except asyncio.CancelledError:
            await self._set(ConnectionState.STOPPED)
        except Exception as e:
            logger.warning(
                "The detached run of %r failed", self.app.identifier, exc_info=True
            )
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
            logger.warning(
                "The connection listener failed on %s", state.value, exc_info=True
            )

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
    url: str | Source = DISCOVER,
    token: str | Source | None = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    force: bool = False,
    connection_listener: "ConnectionListener | None" = None,
    task_listener: "TaskListener | None" = None,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
    supervisor: str | Source | None = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
) -> DetachedRun[None]: ...
@overload
def run_detached(
    app: App[Ctx],
    *,
    context: Ctx,
    url: str | Source = DISCOVER,
    token: str | Source | None = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    force: bool = False,
    connection_listener: "ConnectionListener | None" = None,
    task_listener: "TaskListener | None" = None,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
    supervisor: str | Source | None = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
) -> DetachedRun[Ctx]: ...


def run_detached(
    app: App[Any],
    *,
    context: object = None,
    url: str | Source = DISCOVER,
    token: str | Source | None = DISCOVER,
    mandate_key: str | Source | None = DISCOVER,
    skip_cache: bool = False,
    reauth: bool | Source = DISCOVER,
    headless: bool = False,
    device_code_hook: DeviceCodeHook | None = None,
    force: bool = False,
    connection_listener: "ConnectionListener | None" = None,
    task_listener: "TaskListener | None" = None,
    allow_insecure_transport: bool | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
    supervisor: str | Source | None = DISCOVER,
    mesh: MeshOptions | MeshProxy | bool | Source | None = DISCOVER,
    alias_policy: AliasPolicy | None = None,
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
            mandate_key=mandate_key,
            skip_cache=skip_cache,
            reauth=reauth,
            headless=headless,
            device_code_hook=device_code_hook,
            force=force,
            connection_listener=connection_listener,
            task_listener=task_listener,
            allow_insecure_transport=allow_insecure_transport,
            device_id=device_id,
            supervisor=supervisor,
            mesh=mesh,
            alias_policy=alias_policy,
        ),
    )
    running.start()
    return running


def has_stored_login(
    app: App[Any],
    *,
    url: str | Source = DISCOVER,
    device_id: str | Source | None = DISCOVER,
) -> bool:
    """Whether a run of ``app`` would find a login on this machine and need no approval.

    Nothing connects: it reads the session saved for this app, at this version,
    on this server, and checks that it was approved for what the app declares now
    and has not aged out. The server has the last word when the run connects.

    Args:
        app: The app.
        url: The fakts server, or where to find it (a source, see
            :mod:`arkitekt.app.sources`). Defaults to ``"discover"``: ``--url``,
            ``$FAKTS_URL``, then the public deployment.
        device_id: This device's identity. Defaults to ``"discover"``:
            ``--device-id``, then ``$ARKITEKT_DEVICE_ID``, then the machine's id;
            ``None`` states none.
    """
    session = read_session(session_path(app.identifier, app.version, resolve_url(url)))
    if session is None:
        return False
    return (
        session.is_for(run_manifest(app, device_id).hash())
        and session.state() == "active"
    )


async def _arevoke_stored(
    auth: "AuthFakt", server: str, allow_insecure_transport: bool
) -> None:
    """Revoke a stored session at its server, where the server says how."""
    refresh_token = auth.refresh_token
    if not refresh_token:
        return  # nothing the server could revoke
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
        refresh_token=refresh_token,
        ssl_context=ssl_context,
        allow_insecure_transport=allow_insecure_transport,
    )


def logout(
    app: App[Any],
    *,
    url: str | Source = DISCOVER,
    allow_insecure_transport: bool | Source = DISCOVER,
) -> bool:
    """Revoke ``app``'s login on its server and forget it on this machine.

    The next run needs a new approval. A server that advertises a revocation
    endpoint is told, so the session ends for every holder of a copy; one that
    advertises none (or cannot be reached) leaves the session forgotten here
    only. End a run still going on the session first -- it would write the
    session back when its token rotates.

    Args:
        app: The app.
        url: The fakts server, or where to find it (a source, see
            :mod:`arkitekt.app.sources`). Defaults to ``"discover"``: ``--url``,
            ``$FAKTS_URL``, then the public deployment.
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
        failure: list[BaseException] = []

        def revoke() -> None:
            try:
                asyncio.run(
                    _arevoke_stored(
                        auth,
                        server,
                        resolve_insecure_transport(allow_insecure_transport),
                    )
                )
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
    "RunningApps",
    "Runtime",
    "alogin",
    "arun",
    "arun_all",
    "LocalRun",
    "connect",
    "connect_local",
    "has_stored_login",
    "logout",
    "providing",
    "run",
    "run_all",
    "run_detached",
    "run_manifest",
]
