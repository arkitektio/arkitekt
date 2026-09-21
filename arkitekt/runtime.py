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

import logging
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Type,
    TypeVar,
    cast,
    Generic,
    overload,
)

from fakts import Fakts
from fakts.grants.remote.authorizers.device_code import DeviceCodeHook
from koil import unkoil
from koil.composition import KoiledModel
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from arkitekt.app.app import App, Ctx
from arkitekt.app.fakts import build_fakts
from arkitekt.app.snapshot import RunSnapshot
from arkitekt.device_id import get_or_set_device_id
from koil.bridge import unkoil_task
from rekuest.provider import Provider
from rekuest.service import Service

if TYPE_CHECKING:
    from koil import KoilFuture


logger = logging.getLogger(__name__)

T = TypeVar("T")


class ConnectionOptions(BaseModel):
    """How a run connects. Everything here is about the deployment, nothing about the app.

    What is passed wins; then the environment (``FAKTS_URL``, ``FAKTS_TOKEN``,
    ``FAKTS_REDEEM_TOKEN``); then the defaults. :func:`connect` documents each.
    """

    url: Optional[str] = None
    token: Optional[str] = None
    redeem_token: Optional[str] = None
    no_cache: bool = False
    headless: bool = False
    # Held as Any: pydantic cannot build a schema for the hook's callable type.
    device_code_hook: Optional[Any] = None
    force: bool = False
    """Take over an existing registration of this app's agent. Applied to the
    run's agent; the app and its clients know nothing of it."""
    device_id: Optional[str] = None

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
    def services(self) -> Mapping[str, "Service"]:
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
        return agent

    # ------------------------------------------------------------------ #
    # Entering                                                           #
    # ------------------------------------------------------------------ #

    async def __aenter__(self) -> "Runtime":
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
            # After the clients: the agent's socket opens last and closes first.
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
        unkoil(self.arun, context=context)

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
        return unkoil_task(self.arun, context=context)


def _provider_for(app: App) -> Optional[Provider[Any]]:
    """The provider a run of ``app`` builds its agent from: the app's own, or rekuest's.

    An app offering anything without declaring how it is served is served by
    rekuest; one offering nothing is not served at all.
    """
    declared = app.registry.provider_declaration
    if declared is not None:
        return declared
    if app.registry.is_empty():
        return None
    from rekuest.arkitekt import rekuest_provider

    return rekuest_provider


def connect(
    app: App[Ctx],
    *,
    provide: bool = False,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
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
        no_cache: Skip the fakts cache, and so authenticate again.
        headless: Print the device-code prompt instead of opening a browser.
        device_code_hook: Called with the device code instead of the default prompt.
        force: Take over an existing agent connection of this app.
        device_id: This device's identity. Defaults to the machine's id.

    Returns:
        The runtime, not yet entered.
    """
    return Runtime(
        app=app,
        options=ConnectionOptions(
            url=url,
            token=token,
            redeem_token=redeem_token,
            no_cache=no_cache,
            headless=headless,
            device_code_hook=device_code_hook,
            force=force,
            device_id=device_id,
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
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
) -> None: ...
@overload
def run(
    app: App[Ctx],
    *,
    context: Ctx,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
) -> None: ...


def run(
    app: App[Any],
    *,
    context: Any | None = None,  # noqa: ANN401
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
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
        no_cache: Skip the fakts cache, and so authenticate again.
        headless: Print the device-code prompt instead of opening a browser.
        device_code_hook: Called with the device code instead of the default prompt.
        force: Take over an existing agent connection of this app.
        device_id: This device's identity. Defaults to the machine's id.

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
        no_cache=no_cache,
        headless=headless,
        device_code_hook=device_code_hook,
        force=force,
        device_id=device_id,
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
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
) -> None: ...
@overload
async def arun(
    app: App[Ctx],
    *,
    context: Ctx,
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
) -> None: ...


async def arun(
    app: App[Any],
    *,
    context: Any | None = None,  # noqa: ANN401
    url: Optional[str] = None,
    token: Optional[str] = None,
    redeem_token: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    device_code_hook: Optional[DeviceCodeHook] = None,
    force: bool = False,
    device_id: Optional[str] = None,
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
        no_cache: Skip the fakts cache, and so authenticate again.
        headless: Print the device-code prompt instead of opening a browser.
        device_code_hook: Called with the device code instead of the default prompt.
        force: Take over an existing agent connection of this app.
        device_id: This device's identity. Defaults to the machine's id.

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
        no_cache=no_cache,
        headless=headless,
        device_code_hook=device_code_hook,
        force=force,
        device_id=device_id,
    )
    async with runtime:
        await runtime.arun(context=context)


__all__ = ["Runtime", "ConnectionOptions", "connect", "run", "arun"]
