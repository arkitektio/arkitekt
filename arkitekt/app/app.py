"""The app: a declaration of what it is and what it offers.

An :class:`App` does no I/O and holds no connection. It says who it is (identifier,
version, scopes, ...), which services it uses, and what it offers (actions, states,
hooks, bloks). Running it is someone else's job: :func:`arkitekt.run` provides it,
:func:`arkitekt.connect` only connects, and each of them builds a fresh
:class:`~arkitekt.runtime.Runtime` holding everything stateful.

```python
from arkitekt import App, run
from mikro import Mikro, mikro_service
from mikro.arkitekt.specs import Image, LabelMask

app = App("my-app", version="0.1.0")
app.service(mikro_service)

@app.action
def segment(image: Image, mikro: Mikro) -> LabelMask: ...

if __name__ == "__main__":
    run(app)
```

Because nothing here is stateful, one app can be run any number of times, and
concurrently: each run takes its own snapshot of the registry.
"""

import inspect
import logging
import os
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    ParamSpec,
    Self,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
    dataclass_transform,
    overload,
)

from arkitekt_spec.actions import (
    AssetKind,
    AssignWidgetInput,
    BlokDemoInput,
    ComponentNodeInput,
    EffectInput,
    Effects,
    Execution,
    PortGroupInput,
    TestTargetInput,
    TrackInput,
    ValidatorInput,
)
from arkitekt_spec.declare.actors.policy import KEEP, DisconnectPolicy
from arkitekt_spec.declare.actors.types import Actifier
from arkitekt_spec.declare.app import AppRegistry
from arkitekt_spec.declare.blok.action import ActionBloks
from arkitekt_spec.declare.blok.declarations import Local, Query, Subscription
from arkitekt_spec.declare.catalogs import BlokCheckMode, ComponentSpec, OperationSpec
from arkitekt_spec.declare.coercible_types import OptimisticCoercible
from arkitekt_spec.declare.provider import Provider
from arkitekt_spec.declare.register import WrappedFunction
from arkitekt_spec.declare.service import Service
from arkitekt_spec.declare.structures.convert import AppNamespace, source_root
from arkitekt_spec.declare.structures.model import model_field
from arkitekt_spec.declare.structures.utils import id_shrink
from arkitekt_spec.scalars import JSONSerializable
from fakts.models import Manifest, PublicSource, Requirement

from arkitekt.app.snapshot import RunSnapshot

logger = logging.getLogger(__name__)

#: The variable an image carries the version of its build in; see :class:`App`.
VERSION_ENV = "ARKITEKT_APP_VERSION"

P = ParamSpec("P")
R = TypeVar("R")
C = TypeVar("C", bound=type)
Ctx = TypeVar("Ctx")
"""The app context: what a run hands the agent, ``run(app, context=...)``."""
F = TypeVar("F", bound=Callable[..., Any])


def _merge_requirements(*groups: Iterable[Requirement]) -> List[Requirement]:
    """Merge requirement lists, the first of each key winning.

    Args:
        *groups: Requirement lists, in order of precedence.

    Returns:
        One requirement per key, sorted by key.
    """
    merged: Dict[str, Requirement] = {}
    for group in groups:
        for requirement in group:
            merged.setdefault(requirement.key, requirement)
    return sorted(merged.values(), key=lambda requirement: requirement.key)


def _requirements_of(registry: AppRegistry) -> List[Requirement]:
    """What a registry's services and providers require, merged."""
    return _merge_requirements(
        *(builder.get_requirements() for builder in registry.services.values()),
        *(provider.get_requirements() for provider in registry.providers.values()),
    )


#: The scope every app asks for: it logs a user in.
BASE_SCOPES = ("openid",)


def _scopes_of(registry: AppRegistry, asked: Iterable[str] = ()) -> List[str]:
    """The scopes an app with ``registry`` asks for: its own, what each service's client needs,
    and what its actions' dynamic asks and calls need."""
    return sorted(
        {
            *BASE_SCOPES,
            *asked,
            *(scope for builder in registry.services.values() for scope in builder.get_scopes()),
            *registry.get_scopes(),
        }
    )


def _caller(depth: int = 2) -> Tuple[Path, Optional[str]]:
    """The file and module some caller up the stack is defined in.

    Args:
        depth: How many frames up the caller is; 2 is the caller of the function
            that calls this one.

    Returns:
        That frame's file name -- not a file on disk for code typed into a
        console (``<stdin>``) -- and its module's ``__name__`` (``__main__`` for a
        script that is run).
    """
    frame = inspect.stack()[depth].frame
    name = frame.f_globals.get("__name__")
    # Path, not "/": on Windows a frame's filename uses backslashes.
    return Path(frame.f_code.co_filename), name if isinstance(name, str) else None


def _app_namespace(identifier: str, caller: Tuple[Path, Optional[str]]) -> AppNamespace:
    """The namespace of an app named ``identifier`` constructed by ``caller`` (from
    :func:`_caller`): what counts as the app's own source."""
    constructed_in, module = caller
    return AppNamespace(identifier=identifier, root=source_root(constructed_in), module=module)


def _app_root(constructed_in: Path) -> Path:
    """The directory of an app constructed in the file ``constructed_in``.

    Code typed into a console has no file: its directory is then the working one.
    """
    return constructed_in.resolve().parent if constructed_in.is_file() else Path.cwd()


def _registry_of(app: Union["App[Any]", AppRegistry]) -> AppRegistry:
    return app.registry if isinstance(app, App) else app


def merge(
    first: Union["App[Any]", AppRegistry], /, *others: Union["App[Any]", AppRegistry]
) -> AppRegistry:
    """One new registry holding what the given apps and registries declare.

    Run it as an app of its own, under its own identifier::

        app = App("microscope", registry=merge(stage, camera))

    What several of them share (a service they all use, a registry they all took) counts
    once. Clashing names are refused. See :meth:`App.merge` to merge into an existing app.

    Args:
        first: An app or registry to take.
        others: Any more. None of them is changed.

    Returns:
        The new registry.
    """
    merged = AppRegistry()
    for part in (first, *others):
        merged.merge(_registry_of(part))
    return merged


class App(Generic[Ctx]):
    """What an app is and what it offers. Pure declaration: no I/O, no clients.

    Args:
        identifier: The app's globally unique identifier. Defaults to the name of
            the file that constructs it. It also namespaces the identifiers derived
            for the enums, memory structures and models the app defines itself
            (``@<identifier>/...``), so they are the same however the app is
            launched. A class is the app's own when its module is ``__main__``, the
            module constructing the app, or a file under that module's top-level
            package (or script directory) outside ``site-packages``; any other
            class -- a library's -- keeps the identifier of its module
            (``@numpy/ndarray``), the same in every app.
        version: The app's version. An image built from a branch carries the
            version of that build in ``ARKITEKT_APP_VERSION``, which then wins:
            the source of a branch still names the last release, and an image must
            register as the build it is.
        description: What the app is, in a sentence. It goes into the manifest
            and, from there, onto the agent that provides the app -- shown
            beside its name, which is what tells two agents of the same app
            apart from what they are.
        logo: A public http url of the app's logo.
        scopes: Scopes the app asks for beyond what its services' clients need (those, and ``openid``, are asked for anyway).
        author: Who wrote the app. Used when packaging it.
        public_sources: Public sources the app announces in its manifest.
        services: The services the app uses (``[mikro_service]``). The same as
            calling :meth:`service` for each.
        providers: The provider that serves what the app offers. Without one,
            ``run(app)`` serves it through rekuest's.
        registry: The registry to declare into. A fresh one by default.
        root: The app's directory, which the paths of its assets are relative to.
            Defaults to the directory of the file that constructs the app.
        app_context: The class of the app context: what a run hands the agent
            (``run(app, context=Config(...))``) and what a hook or action
            annotated with it receives. An app declaring one is ``App[Config]``
            and every run of it must pass an instance; one declaring none is
            ``App[None]`` and a run passes nothing.
        effects: What running an action again would do to the world, for the
            actions that don't say themselves. A robot sets
            ``Effects.IRREVERSIBLE`` once. Informational: shown to whoever
            decides about a lost task.

    Raises:
        TypeError: If something other than a service is given.
        ValueError: If two services of one name are given.
    """

    @overload
    def __init__(
        self: "App[None]",
        identifier: Optional[str] = None,
        version: str = "0.0.1",
        *,
        description: Optional[str] = None,
        logo: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        author: Optional[str] = None,
        public_sources: Optional[List[PublicSource]] = None,
        services: Sequence["Service[Any]"] = (),
        providers: Sequence["Provider[Any]"] = (),
        registry: Optional[AppRegistry] = None,
        root: Optional[Union[str, Path]] = None,
        app_context: None = None,
        effects: Optional[Effects] = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        identifier: Optional[str] = None,
        version: str = "0.0.1",
        *,
        description: Optional[str] = None,
        logo: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        author: Optional[str] = None,
        public_sources: Optional[List[PublicSource]] = None,
        services: Sequence["Service[Any]"] = (),
        providers: Sequence["Provider[Any]"] = (),
        registry: Optional[AppRegistry] = None,
        root: Optional[Union[str, Path]] = None,
        app_context: type[Ctx],
        effects: Optional[Effects] = None,
    ) -> None: ...

    def __init__(
        self,
        identifier: Optional[str] = None,
        version: str = "0.0.1",
        *,
        description: Optional[str] = None,
        logo: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        author: Optional[str] = None,
        public_sources: Optional[List[PublicSource]] = None,
        services: Sequence["Service[Any]"] = (),
        providers: Sequence["Provider[Any]"] = (),
        registry: Optional[AppRegistry] = None,
        root: Optional[Union[str, Path]] = None,
        app_context: Optional[type[Ctx]] = None,
        effects: Optional[Effects] = None,
    ) -> None:
        caller = _caller()
        constructed_in = caller[0]
        self.identifier: str = identifier or constructed_in.stem
        self.version = os.environ.get(VERSION_ENV) or version
        self.description = description
        self.logo = logo
        # What the app asks for beyond what its services' clients need (see `scopes`).
        self.asked_scopes: List[str] = list(scopes or [])
        self.author = author
        self.public_sources: List[PublicSource] = list(public_sources or [])
        self.registry: AppRegistry = registry if registry is not None else AppRegistry()
        # What a derived identifier (an enum's, a memory structure's, a model's) is
        # namespaced by: the app for a class it defines itself, never the module
        # that class happens to be in -- `__main__` when the app's file is run, its
        # name when it is imported. Library classes keep their module's.
        # A wrapper constructing the app for its caller (QtApp, easy()) sets it again
        # from that caller.
        self.registry.structure_registry.namespace = _app_namespace(self.identifier, caller)
        if root is not None:
            self.registry.root = Path(root).resolve()
        elif self.registry.root is None:
            self.registry.root = _app_root(constructed_in)
        if app_context is not None:
            self.registry.app_context(app_context)
        if effects is not None:
            # What running an action again would do, for the actions that don't say.
            self.registry.default_effects = effects
        self.service(*services)
        self.provider(*providers)

    @property
    def app_context(self) -> Optional[type[Ctx]]:
        """The class a run's ``context=`` must be an instance of, or ``None``.

        Read off the registry, which is where the declaration lives: an app made
        over a registry that already declares one reports it too.
        """
        return cast(Optional[type[Ctx]], self.registry.app_context_class)

    def __repr__(self) -> str:
        return f"App({self.identifier!r}, version={self.version!r}, services={self.services!r})"

    # ------------------------------------------------------------------ #
    # Services                                                           #
    # ------------------------------------------------------------------ #

    def service(self, *services: "Service[Any]") -> Self:
        """Use these services: ``app.service(mikro_service)``.

        Each is registered on this app's registry, which takes in its structures
        and implementations right away, so an action registered next can name
        their types. Registering a service twice does nothing. A parameter
        annotated with what a registered service returns (``mikro: Mikro``) is
        handed that client; one annotated with a class no registered service
        returns is a port, and is refused as unregistered when the action is
        registered.

        Args:
            *services: The services, as their packages export them
                (``from mikro import mikro_service``).

        Returns:
            The app, so calls chain.

        Raises:
            TypeError: If something other than a service is given -- a client
                class, say. There is no catalog to look one up in.
            ValueError: If a second service of an already registered name is given.
        """
        for declared in services:
            if not isinstance(declared, Service):
                shown = declared.__name__ if isinstance(declared, type) else repr(declared)
                raise TypeError(
                    f"{shown} is not a service. Pass the service object the package "
                    f"exports, e.g. `from mikro import mikro_service`; there is no "
                    "catalog to look a client class up in."
                )
            self.registry.register_service(declared)
        return self

    def provider(self, *providers: "Provider[Any]") -> Self:
        """Serve what this app offers through these providers: ``app.provider(...)``.

        A provider builds the agent a run drives; an app is served by one. Each
        is registered on this app's registry, which takes in the service beside
        it and the structures its package brings.

        Raises:
            TypeError: If something other than a provider is given.
            ValueError: If a different provider is registered already.
        """
        for declared in providers:
            if not isinstance(declared, Provider):
                shown = declared.__name__ if isinstance(declared, type) else repr(declared)
                raise TypeError(
                    f"{shown} is not a provider. Pass the provider object the package "
                    "exports, e.g. `from rekuest.arkitekt import rekuest_provider`."
                )
            self.registry.register_provider(declared)
        return self

    @property
    def services(self) -> List[str]:
        """The names of the services this app uses, in the order they were registered."""
        return list(self.registry.services)

    @property
    def service_builders(self) -> Dict[str, "Service[Any]"]:
        """The services this app uses, by name: what a runtime builds clients from."""
        return dict(self.registry.services)

    # ------------------------------------------------------------------ #
    # Identity                                                           #
    # ------------------------------------------------------------------ #

    @property
    def scopes(self) -> List[str]:
        """What this app asks to be allowed to do: what its services' clients need, and its own.

        Each service says what its client's operations need at the server (its
        generated code gathers it from the schema), so an app rarely names a
        scope itself: ``App(scopes=...)`` adds to them, for something no client
        here does. A run adds what its provider's services need; see
        :meth:`snapshot`.
        """
        return _scopes_of(self.registry, self.asked_scopes)

    @property
    def requirements(self) -> List[Requirement]:
        """What this app requires of a deployment: exactly what its services need.

        An app cannot require anything on its own. Everything it needs from a
        deployment comes through a service, which is also what builds the client
        for it -- so to need another deployment service, declare (or write) the
        :meth:`~rekuest.app.AppRegistry.service` for it. A run adds what its
        provider requires (rekuest's, for ``run(app)``); see :meth:`snapshot`.
        """
        return _requirements_of(self.registry)

    @property
    def manifest(self) -> Manifest:
        """What this app tells the server it is. Pure data, read off the declaration.

        It carries no device id: that names the device a run happens on, and the
        runtime adds it.
        """
        from arkitekt.app.spec import app_manifest

        # The login manifest is the spec's AppManifest plus the login-only fields,
        # built from the same identity every other shape of the app is.
        return Manifest(
            **dict(app_manifest(self)),
            requirements=self.requirements,
            public_sources=list(self.public_sources),
        )

    def snapshot(
        self, device_id: Optional[str] = None, provider: Optional["Provider[Any]"] = None
    ) -> "RunSnapshot":
        """Take what a run of this app would serve, without connecting.

        Everything a run needs to know about the app, taken together so the two
        parts cannot drift: the manifest, and the frozen registry with the
        services on it. A run takes its own; this is also how an app is inspected.

        Args:
            device_id: The device the run happens on, written into the manifest.
                ``None`` leaves it unset, which is what inspecting an app wants.
            provider: The provider the run builds its agent from. One this app
                did not declare (rekuest's, for ``run(app)``) is taken into the
                run's registry -- with the service and structures its package
                brings -- and its requirements into the run's manifest. The app
                itself is left as declared.

        Returns:
            The snapshot: validated, frozen, with no clients bound.

        Raises:
            StructureRegistryError: If a port names a structure this app cannot
                resolve -- usually a service it does not declare.
        """
        registry = self.registry
        if provider is not None and provider.name not in registry.providers:
            registry = AppRegistry()
            registry.merge(self.registry)
            registry.register_provider(provider)

        manifest = self.manifest.model_copy(
            update={"requirements": _requirements_of(registry), "scopes": _scopes_of(registry, self.asked_scopes)}
        )
        if device_id is not None:
            manifest = manifest.model_copy(update={"device_id": device_id})
        return RunSnapshot(manifest=manifest, registry=registry.snapshot())

    # ------------------------------------------------------------------ #
    # What the app offers                                                #
    # ------------------------------------------------------------------ #

    @overload
    def action(self, function: Callable[P, R], /) -> WrappedFunction[P, R]: ...

    @overload
    def action(
        self,
        /,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        actifier: Actifier | None = None,
        interface: Optional[str] = None,
        stateful: bool = False,
        widgets: Optional[Dict[str, AssignWidgetInput]] = None,
        collections: Optional[List[str]] = None,
        port_groups: Optional[List[PortGroupInput]] = None,
        port_effects: Optional[Dict[str, List[EffectInput]]] = None,
        is_test_for: Optional[List[TestTargetInput]] = None,
        validators: Optional[Dict[str, List[ValidatorInput]]] = None,
        optimistics: Optional[List[OptimisticCoercible]] = None,
        in_process: bool = False,
        tracks: Optional[List[TrackInput]] = None,
        locks: Optional[List[str]] = None,
        concurrency: Literal["parallel", "serial"] = "serial",
        policy: DisconnectPolicy = KEEP,
        version: Optional[str] = None,
        catalogs: Optional[List[str]] = None,
        protocols: Optional[List[str]] = None,
        effects: Optional[Effects] = None,
        logo: Optional[Union[str, ComponentNodeInput]] = None,
        bloks: Optional[ActionBloks] = None,
        dynamic_asks: bool = False,
        dynamic_calls: bool = False,
        dynamic_informs: bool = False,
        estimated_runtime: Optional[str] = None,
        estimated_runtime_ui: Optional[str] = None,
    ) -> Callable[[Callable[P, R]], WrappedFunction[P, R]]: ...

    def action(
        self,
        function: Optional[Callable[P, R]] = None,
        /,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        actifier: Actifier | None = None,
        interface: Optional[str] = None,
        stateful: bool = False,
        widgets: Optional[Dict[str, AssignWidgetInput]] = None,
        collections: Optional[List[str]] = None,
        port_groups: Optional[List[PortGroupInput]] = None,
        port_effects: Optional[Dict[str, List[EffectInput]]] = None,
        is_test_for: Optional[List[TestTargetInput]] = None,
        validators: Optional[Dict[str, List[ValidatorInput]]] = None,
        optimistics: Optional[List[OptimisticCoercible]] = None,
        in_process: bool = False,
        tracks: Optional[List[TrackInput]] = None,
        locks: Optional[List[str]] = None,
        concurrency: Literal["parallel", "serial"] = "serial",
        policy: DisconnectPolicy = KEEP,
        version: Optional[str] = None,
        catalogs: Optional[List[str]] = None,
        protocols: Optional[List[str]] = None,
        effects: Optional[Effects] = None,
        logo: Optional[Union[str, ComponentNodeInput]] = None,
        bloks: Optional[ActionBloks] = None,
        dynamic_asks: bool = False,
        dynamic_calls: bool = False,
        dynamic_informs: bool = False,
        estimated_runtime: Optional[str] = None,
        estimated_runtime_ui: Optional[str] = None,
    ) -> Union[WrappedFunction[P, R], Callable[[Callable[P, R]], WrappedFunction[P, R]]]:
        """Offer a function as an action: ``@app.action`` or ``@app.action(name=...)``.

        Parameters annotated with a client class (``mikro: Mikro``) or with
        :class:`~arkitekt_spec.declare.task.Task` are injected rather than becoming ports, and
        declare their service on this app.

        Args:
            function: The function, when used bare as ``@app.action``.
            name: Display name. Defaults to the function name.
            description: Description. Defaults to the docstring.
            actifier: A runtime's actifier, for actions a particular kind of actor
                must run (the Qt helpers pass theirs). ``None`` leaves it to the
                runtime that runs the app.
            interface: Interface the action is offered at. Defaults to one derived
                from its name.
            stateful: Mark the definition stateful (set automatically when it uses
                states).
            widgets: Widgets per argument.
            collections: Collections the action is grouped into.
            port_groups: Port group assignments.
            port_effects: UI effects per port (hide, disable, … as its values change).
            is_test_for: Actions this one tests.
            validators: Input validation rules per argument.
            optimistics: Optimistic outputs.
            in_process: Run in the event loop instead of a worker thread.
            tracks: Tracks the implementation follows.
            locks: Locks held while an assignment runs.
            concurrency: Whether assignments may run concurrently.
            policy: What happens to a running assignment when its caller
                disconnects.
            version: Version of the definition.
            catalogs: Catalogs the action is listed in.
            protocols: Where the action means to hook in (``on_scene_annotation``):
                hints a caller filters on to find it, never a contract.
            effects: What running it again would do to the world. Informational:
                shown to whoever decides about a lost task. Defaults to the app's
                ``effects``.
            logo: The logo that draws the action: the name of an action logo blok
                this app declares (``app.blok(name, "<ActionLogo>...</ActionLogo>")``), or a
                tree of its own (``bsx("<ActionLogo>...</ActionLogo>")``). Without
                one, a client shows the app's default logo.
            bloks: The action's own bloks, one per context, which each one's root
                names: an ``"<Overlay>...</Overlay>"`` is drawn into the space that hosts
                the run, its ``<Anchor dep="robot">`` anchored at the agent the run got
                for that parameter; an ``"<Html>...</Html>"`` is a task panel. A bare
                tree, or an ``ActionBlok`` for locals and the like; one needs no list.
                They name devices only by the function's dependency
                parameters, read the run under ``@task``, are checked now, and are not
                part of the action's hash.
            dynamic_asks: Whether a task may also ask through a blok made at ask time
                (``task.dynamic_ask``), not only its asks (``@ask`` on an interactions
                protocol it is handed). The app then asks for the ``rekuest_dynamic_ask`` scope.
            dynamic_calls: Whether a task may also call actions it found at run time
                (``task.call``), not only its dependencies. A workflow only; the app then
                asks for the ``rekuest_dynamic_call`` scope.
            dynamic_informs: Whether a task may show a blok made at inform time
                (``task.dynamic_inform``), not only its informs (``@inform``). The app
                then asks for the ``rekuest_dynamic_inform`` scope.
            estimated_runtime: A formula for how long it runs, in seconds, such as
                ``'args.image["@mikro/size"] / agent.cpu_count / 5e7'``. Parsed at
                declaration, never run. The action query filters and sorts by it, so it
                is refused unless the server can compute it: arithmetic over one
                structure argument's descriptors and the agent's hardware.
            estimated_runtime_ui: A richer formula for the form only, shown instead of
                ``estimated_runtime``, which it requires: any pure function, and the
                form's values too. The two can disagree.

        Returns:
            The function, still callable as itself -- pass it its clients and a
            :meth:`Task.local() <arkitekt_spec.declare.task.Task.local>` to call it with no
            runtime -- or, with options, a decorator returning it.

        Raises:
            DefinitionError: If a parameter cannot become a port, e.g. a
                structure of a service this app does not declare.
        """

        def offer(function: Callable[P, R]) -> WrappedFunction[P, R]:
            return self.register_action(
                function,
                name=name,
                description=description,
                actifier=actifier,
                interface=interface,
                stateful=stateful,
                widgets=widgets,
                collections=collections,
                port_groups=port_groups,
                port_effects=port_effects,
                is_test_for=is_test_for,
                validators=validators,
                optimistics=optimistics,
                in_process=in_process,
                tracks=tracks,
                locks=locks,
                concurrency=concurrency,
                policy=policy,
                version=version,
                catalogs=catalogs,
                protocols=protocols,
                effects=effects,
                logo=logo,
                bloks=bloks,
                dynamic_asks=dynamic_asks,
                dynamic_calls=dynamic_calls,
                dynamic_informs=dynamic_informs,
                estimated_runtime=estimated_runtime,
                estimated_runtime_ui=estimated_runtime_ui,
            )

        if function is not None:
            return offer(function)
        return offer

    def register_action(
        self,
        function: Callable[P, R],
        /,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        actifier: Actifier | None = None,
        interface: Optional[str] = None,
        stateful: bool = False,
        widgets: Optional[Dict[str, AssignWidgetInput]] = None,
        collections: Optional[List[str]] = None,
        port_groups: Optional[List[PortGroupInput]] = None,
        port_effects: Optional[Dict[str, List[EffectInput]]] = None,
        is_test_for: Optional[List[TestTargetInput]] = None,
        validators: Optional[Dict[str, List[ValidatorInput]]] = None,
        optimistics: Optional[List[OptimisticCoercible]] = None,
        in_process: bool = False,
        tracks: Optional[List[TrackInput]] = None,
        locks: Optional[List[str]] = None,
        concurrency: Literal["parallel", "serial"] = "serial",
        policy: DisconnectPolicy = KEEP,
        version: Optional[str] = None,
        catalogs: Optional[List[str]] = None,
        protocols: Optional[List[str]] = None,
        effects: Optional[Effects] = None,
        logo: Optional[Union[str, ComponentNodeInput]] = None,
        bloks: Optional[ActionBloks] = None,
        dynamic_asks: bool = False,
        dynamic_calls: bool = False,
        dynamic_informs: bool = False,
        estimated_runtime: Optional[str] = None,
        estimated_runtime_ui: Optional[str] = None,
    ) -> WrappedFunction[P, R]:
        """Offer a function as an action, as a plain call: ``app.register_action(function, name=...)``.

        The twin of :meth:`action`, with the same options, for a function that is
        declared somewhere else or offered only under a condition.

        Returns:
            The function, still callable as itself.

        Raises:
            DefinitionError: If a parameter cannot become a port, e.g. a
                structure of a service this app does not declare.
        """
        # Through the registry rather than rekuest's module-level decorator: the registry
        # is what owns the declaration, and it supplies itself and its structures. The cast
        # is because `AppRegistry.register` forwards `**kwargs` untyped -- this method's own
        # signature is what types the surface a user sees.
        decorate = cast(
            "Callable[[Callable[P, R]], WrappedFunction[P, R]]",
            self.registry.register(
                name=name,
                description=description,
                actifier=actifier,
                interface=interface,
                stateful=stateful,
                widgets=widgets,
                collections=collections,
                port_groups=port_groups,
                port_effects=port_effects,
                is_test_for=is_test_for,
                validators=validators,
                optimistics=optimistics,
                in_process=in_process,
                tracks=tracks,
                locks=locks,
                concurrency=concurrency,
                policy=policy,
                version=version,
                catalogs=catalogs,
                protocols=protocols,
                effects=effects,
                logo=logo,
                # Only when given, so an arkitekt-spec without action bloks still registers the rest.
                **({"bloks": bloks} if bloks else {}),
                # The same for the dynamic flags: an arkitekt-spec without them registers the rest.
                **({"dynamic_asks": True} if dynamic_asks else {}),
                **({"dynamic_calls": True} if dynamic_calls else {}),
                **({"dynamic_informs": True} if dynamic_informs else {}),
                **({"estimated_runtime": estimated_runtime} if estimated_runtime else {}),
                **({"estimated_runtime_ui": estimated_runtime_ui} if estimated_runtime_ui else {}),
            ),
        )
        return decorate(function)

    @overload
    def workflow(self, function: Callable[P, R], /) -> WrappedFunction[P, R]: ...

    @overload
    def workflow(
        self,
        /,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        actifier: Actifier | None = None,
        interface: Optional[str] = None,
        stateful: bool = False,
        widgets: Optional[Dict[str, AssignWidgetInput]] = None,
        collections: Optional[List[str]] = None,
        port_groups: Optional[List[PortGroupInput]] = None,
        port_effects: Optional[Dict[str, List[EffectInput]]] = None,
        is_test_for: Optional[List[TestTargetInput]] = None,
        validators: Optional[Dict[str, List[ValidatorInput]]] = None,
        optimistics: Optional[List[OptimisticCoercible]] = None,
        in_process: bool = False,
        tracks: Optional[List[TrackInput]] = None,
        locks: Optional[List[str]] = None,
        concurrency: Literal["parallel", "serial"] = "serial",
        policy: DisconnectPolicy = KEEP,
        version: Optional[str] = None,
        catalogs: Optional[List[str]] = None,
        protocols: Optional[List[str]] = None,
        effects: Optional[Effects] = None,
        logo: Optional[Union[str, ComponentNodeInput]] = None,
        bloks: Optional[ActionBloks] = None,
        dynamic_asks: bool = False,
        dynamic_calls: bool = False,
        dynamic_informs: bool = False,
        estimated_runtime: Optional[str] = None,
        estimated_runtime_ui: Optional[str] = None,
    ) -> Callable[[Callable[P, R]], WrappedFunction[P, R]]: ...

    def workflow(
        self,
        function: Optional[Callable[P, R]] = None,
        /,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        actifier: Actifier | None = None,
        interface: Optional[str] = None,
        stateful: bool = False,
        widgets: Optional[Dict[str, AssignWidgetInput]] = None,
        collections: Optional[List[str]] = None,
        port_groups: Optional[List[PortGroupInput]] = None,
        port_effects: Optional[Dict[str, List[EffectInput]]] = None,
        is_test_for: Optional[List[TestTargetInput]] = None,
        validators: Optional[Dict[str, List[ValidatorInput]]] = None,
        optimistics: Optional[List[OptimisticCoercible]] = None,
        in_process: bool = False,
        tracks: Optional[List[TrackInput]] = None,
        locks: Optional[List[str]] = None,
        concurrency: Literal["parallel", "serial"] = "serial",
        policy: DisconnectPolicy = KEEP,
        version: Optional[str] = None,
        catalogs: Optional[List[str]] = None,
        protocols: Optional[List[str]] = None,
        effects: Optional[Effects] = None,
        logo: Optional[Union[str, ComponentNodeInput]] = None,
        bloks: Optional[ActionBloks] = None,
        dynamic_asks: bool = False,
        dynamic_calls: bool = False,
        dynamic_informs: bool = False,
        estimated_runtime: Optional[str] = None,
        estimated_runtime_ui: Optional[str] = None,
    ) -> Union[WrappedFunction[P, R], Callable[[Callable[P, R]], WrappedFunction[P, R]]]:
        """Offer a workflow: an action that may call other actions. ``@app.workflow``.

        It is called exactly like an action. What differs is what happens when its
        agent dies: it is resumed, not lost. Calls it already made return their
        recorded results instead of running again, and values it took through the
        task (``task.now()``, ``task.record(...)``) come back the same. So its code
        must be deterministic: outside values come in only through calls and the task.

        A step whose own agent dies raises ``AgentLost`` at the call; handle it like
        any exception, or with ``task.retry(...)`` / ``task.hold(...)``.

        Parameters annotated with a client class (``mikro: Mikro``) or with
        :class:`~arkitekt_spec.declare.task.Task` are injected rather than becoming ports, and
        declare their service on this app.

        Args:
            function: The function, when used bare as ``@app.action``.
            name: Display name. Defaults to the function name.
            description: Description. Defaults to the docstring.
            actifier: A runtime's actifier, for actions a particular kind of actor
                must run (the Qt helpers pass theirs). ``None`` leaves it to the
                runtime that runs the app.
            interface: Interface the action is offered at. Defaults to one derived
                from its name.
            stateful: Mark the definition stateful (set automatically when it uses
                states).
            widgets: Widgets per argument.
            collections: Collections the action is grouped into.
            port_groups: Port group assignments.
            port_effects: UI effects per port (hide, disable, … as its values change).
            is_test_for: Actions this one tests.
            validators: Input validation rules per argument.
            optimistics: Optimistic outputs.
            in_process: Run in the event loop instead of a worker thread.
            tracks: Tracks the implementation follows.
            locks: Locks held while an assignment runs.
            concurrency: Whether assignments may run concurrently.
            policy: What happens to a running assignment when its caller
                disconnects.
            version: Version of the definition.
            catalogs: Catalogs the action is listed in.
            protocols: Where the action means to hook in (``on_scene_annotation``):
                hints a caller filters on to find it, never a contract.
            effects: What running it again would do to the world. Informational:
                shown to whoever decides about a lost task. Defaults to the app's
                ``effects``.
            logo: The logo that draws the action: the name of an action logo blok
                this app declares (``app.blok(name, "<ActionLogo>...</ActionLogo>")``), or a
                tree of its own (``bsx("<ActionLogo>...</ActionLogo>")``). Without
                one, a client shows the app's default logo.
            bloks: The action's own bloks, one per context, which each one's root
                names: an ``"<Overlay>...</Overlay>"`` is drawn into the space that hosts
                the run, its ``<Anchor dep="robot">`` anchored at the agent the run got
                for that parameter; an ``"<Html>...</Html>"`` is a task panel. A bare
                tree, or an ``ActionBlok`` for locals and the like; one needs no list.
                They name devices only by the function's dependency
                parameters, read the run under ``@task``, are checked now, and are not
                part of the action's hash.
            dynamic_asks: Whether a task may also ask through a blok made at ask time
                (``task.dynamic_ask``), not only its asks (``@ask`` on an interactions
                protocol it is handed). The app then asks for the ``rekuest_dynamic_ask`` scope.
            dynamic_calls: Whether a task may also call actions it found at run time
                (``task.call``), not only its dependencies. A workflow only; the app then
                asks for the ``rekuest_dynamic_call`` scope.
            dynamic_informs: Whether a task may show a blok made at inform time
                (``task.dynamic_inform``), not only its informs (``@inform``). The app
                then asks for the ``rekuest_dynamic_inform`` scope.
            estimated_runtime: A formula for how long it runs, in seconds, such as
                ``'args.image["@mikro/size"] / agent.cpu_count / 5e7'``. Parsed at
                declaration, never run. The action query filters and sorts by it, so it
                is refused unless the server can compute it: arithmetic over one
                structure argument's descriptors and the agent's hardware.
            estimated_runtime_ui: A richer formula for the form only, shown instead of
                ``estimated_runtime``, which it requires: any pure function, and the
                form's values too. The two can disagree.

        Returns:
            The function, still callable as itself -- pass it its clients and a
            :meth:`Task.local() <arkitekt_spec.declare.task.Task.local>` to call it with no
            runtime -- or, with options, a decorator returning it.

        Raises:
            DefinitionError: If a parameter cannot become a port, e.g. a
                structure of a service this app does not declare.
        """

        def offer(function: Callable[P, R]) -> WrappedFunction[P, R]:
            return self.register_workflow(
                function,
                name=name,
                description=description,
                actifier=actifier,
                interface=interface,
                stateful=stateful,
                widgets=widgets,
                collections=collections,
                port_groups=port_groups,
                port_effects=port_effects,
                is_test_for=is_test_for,
                validators=validators,
                optimistics=optimistics,
                in_process=in_process,
                tracks=tracks,
                locks=locks,
                concurrency=concurrency,
                policy=policy,
                version=version,
                catalogs=catalogs,
                protocols=protocols,
                effects=effects,
                logo=logo,
                bloks=bloks,
                dynamic_asks=dynamic_asks,
                dynamic_calls=dynamic_calls,
                dynamic_informs=dynamic_informs,
                estimated_runtime=estimated_runtime,
                estimated_runtime_ui=estimated_runtime_ui,
            )

        if function is not None:
            return offer(function)
        return offer

    def register_workflow(
        self,
        function: Callable[P, R],
        /,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        actifier: Actifier | None = None,
        interface: Optional[str] = None,
        stateful: bool = False,
        widgets: Optional[Dict[str, AssignWidgetInput]] = None,
        collections: Optional[List[str]] = None,
        port_groups: Optional[List[PortGroupInput]] = None,
        port_effects: Optional[Dict[str, List[EffectInput]]] = None,
        is_test_for: Optional[List[TestTargetInput]] = None,
        validators: Optional[Dict[str, List[ValidatorInput]]] = None,
        optimistics: Optional[List[OptimisticCoercible]] = None,
        in_process: bool = False,
        tracks: Optional[List[TrackInput]] = None,
        locks: Optional[List[str]] = None,
        concurrency: Literal["parallel", "serial"] = "serial",
        policy: DisconnectPolicy = KEEP,
        version: Optional[str] = None,
        catalogs: Optional[List[str]] = None,
        protocols: Optional[List[str]] = None,
        effects: Optional[Effects] = None,
        logo: Optional[Union[str, ComponentNodeInput]] = None,
        bloks: Optional[ActionBloks] = None,
        dynamic_asks: bool = False,
        dynamic_calls: bool = False,
        dynamic_informs: bool = False,
        estimated_runtime: Optional[str] = None,
        estimated_runtime_ui: Optional[str] = None,
    ) -> WrappedFunction[P, R]:
        """Offer a function as a workflow, as a plain call: ``app.register_workflow(function, name=...)``.

        The twin of :meth:`workflow`, with the same options, for a function that is
        declared somewhere else or offered only under a condition.

        Returns:
            The function, still callable as itself.

        Raises:
            DefinitionError: If a parameter cannot become a port, e.g. a
                structure of a service this app does not declare.
        """
        # Through the registry rather than rekuest's module-level decorator: the registry
        # is what owns the declaration, and it supplies itself and its structures. The cast
        # is because `AppRegistry.register` forwards `**kwargs` untyped -- this method's own
        # signature is what types the surface a user sees.
        decorate = cast(
            "Callable[[Callable[P, R]], WrappedFunction[P, R]]",
            self.registry.register(
                name=name,
                description=description,
                actifier=actifier,
                interface=interface,
                stateful=stateful,
                widgets=widgets,
                collections=collections,
                port_groups=port_groups,
                port_effects=port_effects,
                is_test_for=is_test_for,
                validators=validators,
                optimistics=optimistics,
                in_process=in_process,
                tracks=tracks,
                locks=locks,
                concurrency=concurrency,
                policy=policy,
                version=version,
                catalogs=catalogs,
                protocols=protocols,
                effects=effects,
                logo=logo,
                execution=Execution.WORKFLOW,
                # Only when given, so an arkitekt-spec without action bloks still registers the rest.
                **({"bloks": bloks} if bloks else {}),
                # The same for the dynamic flags: an arkitekt-spec without them registers the rest.
                **({"dynamic_asks": True} if dynamic_asks else {}),
                **({"dynamic_calls": True} if dynamic_calls else {}),
                **({"dynamic_informs": True} if dynamic_informs else {}),
                **({"estimated_runtime": estimated_runtime} if estimated_runtime else {}),
                **({"estimated_runtime_ui": estimated_runtime_ui} if estimated_runtime_ui else {}),
            ),
        )
        return decorate(function)

    @overload
    def state(
        self,
        cls: C,
        /,
        *,
        name: Optional[str] = None,
        required_locks: Optional[List[str]] = None,
        persist: Union[Literal["synchronous"], float, None] = None,
    ) -> C: ...

    @overload
    def state(
        self,
        /,
        *,
        name: Optional[str] = None,
        required_locks: Optional[List[str]] = None,
        persist: Union[Literal["synchronous"], float, None] = None,
    ) -> Callable[[C], C]: ...

    @dataclass_transform(field_specifiers=(model_field,))
    def state(
        self,
        cls: Optional[C] = None,
        /,
        *,
        name: Optional[str] = None,
        required_locks: Optional[List[str]] = None,
        persist: Union[Literal["synchronous"], float, None] = None,
    ) -> Union[C, Callable[[C], C]]:
        """Declare a class as a state other apps can observe: ``@app.state``.

        Args:
            cls: The class, when used bare as ``@app.state``.
            name: The interface the state is offered at. Defaults to the class name.
            required_locks: Locks every action taking the state holds (inferred), so
                no two actions command it at once. Not a write guard.
            persist: Keep its last value on disk, so a startup hook of the next run can
                take it as ``old: ThisState | None``: ``"synchronous"`` for every change
                (an fsync on the event loop), or a period in seconds. ``None`` keeps
                nothing, and such a state cannot be taken by a startup hook.

        Returns:
            The class, or, with options, a decorator returning it.
        """

        def declare(cls: C) -> C:
            return self.register_state(
                cls, name=name, required_locks=required_locks, persist=persist
            )

        if cls is not None:
            return declare(cls)
        return declare

    @dataclass_transform(field_specifiers=(model_field,))
    def register_state(
        self,
        cls: C,
        /,
        *,
        name: Optional[str] = None,
        required_locks: Optional[List[str]] = None,
        persist: Union[Literal["synchronous"], float, None] = None,
    ) -> C:
        """Declare a class as a state, as a plain call: the twin of :meth:`state`.

        Returns:
            The class.
        """
        self.registry.state(cls, name=name, required_locks=required_locks, persist=persist)
        return cls

    @overload
    def context(self, cls: C, /) -> C: ...

    @overload
    def context(
        self, /, *, name: Optional[str] = None, locks: Optional[List[str]] = None
    ) -> Callable[[C], C]: ...

    def context(
        self,
        cls: Optional[C] = None,
        /,
        *,
        name: Optional[str] = None,
        locks: Optional[List[str]] = None,
    ) -> Union[C, Callable[[C], C]]:
        """Declare a context class: shared by actions, built by a startup hook. ``@app.context``.

        Nothing is written on the class; what this app knows about it lives on
        its registry.

        Args:
            cls: The class, when used bare as ``@app.context``.
            name: The name the agent keeps the context under. Defaults to the
                snake_case class name.
            locks: Lock names an action holding this context must hold.

        Returns:
            The class, or, with options, a decorator returning it.
        """

        def declare(cls: C) -> C:
            return self.register_context(cls, name=name, locks=locks)

        if cls is not None:
            return declare(cls)
        return declare

    def register_context(
        self, cls: C, /, *, name: Optional[str] = None, locks: Optional[List[str]] = None
    ) -> C:
        """Declare a context class, as a plain call: the twin of :meth:`context`.

        Returns:
            The class.
        """
        self.registry.context(cls, name=name, locks=locks)
        return cls

    @overload
    def model(
        self, cls: C, /, *, identifier: Optional[str] = None, description: Optional[str] = None
    ) -> C: ...

    @overload
    def model(
        self, /, *, identifier: Optional[str] = None, description: Optional[str] = None
    ) -> Callable[[C], C]: ...

    @dataclass_transform(field_specifiers=(model_field,))
    def model(
        self,
        cls: Optional[C] = None,
        /,
        *,
        identifier: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Union[C, Callable[[C], C]]:
        """Declare a model: a class whose instances travel by value, field by field. ``@app.model``.

        The class is made a dataclass if it is not one. A port annotated with it
        has one child per field; a model used inside another model is declared
        too.

        Args:
            cls: The class, when used bare as ``@app.model``.
            identifier: What it travels as, ``@package/key``. Defaults to
                ``@<this app's identifier>/<snake_case class name>``.
            description: What it is, for the UI. Defaults to the class docstring.

        Returns:
            The class, or, with options, a decorator returning it.

        Raises:
            StructureDefinitionError: If the identifier is not ``@package/key``.
        """

        def declare(cls: C) -> C:
            return self.register_model(cls, identifier=identifier, description=description)

        if cls is not None:
            return declare(cls)
        return declare

    @dataclass_transform(field_specifiers=(model_field,))
    def register_model(
        self,
        cls: C,
        /,
        *,
        identifier: Optional[str] = None,
        description: Optional[str] = None,
    ) -> C:
        """Declare a model, as a plain call: the twin of :meth:`model`.

        Returns:
            The class, made a dataclass.

        Raises:
            StructureDefinitionError: If the identifier is not ``@package/key``.
        """
        return cast(
            C,
            self.registry.model(
                cls,
                identifier=identifier,
                description=description,
            ),
        )

    def _hook(
        self, kind: str, function: Optional[F], name: Optional[str]
    ) -> Union[F, Callable[[F], F]]:
        def hook(function: F) -> F:
            return self._register_hook(kind, function, name)

        if function is not None:
            return hook(function)
        return hook

    def _register_hook(self, kind: str, function: F, name: Optional[str]) -> F:
        getattr(self.registry, kind)(function, name=name)
        return function

    @overload
    def startup(self, function: F, /) -> F: ...

    @overload
    def startup(self, /, *, name: Optional[str] = None) -> Callable[[F], F]: ...

    def startup(
        self, function: Optional[F] = None, /, *, name: Optional[str] = None
    ) -> Union[F, Callable[[F], F]]:
        """Run a function when the app starts providing: ``@app.startup``.

        What it returns sets up the app's states and contexts.

        Args:
            function: The function, when used bare as ``@app.startup``.
            name: The hook's name. Defaults to the function name.

        Returns:
            The function, or, with options, a decorator returning it.
        """
        return self._hook("startup", function, name)

    def register_startup(self, function: F, /, *, name: Optional[str] = None) -> F:
        """Run a function when the app starts providing, as a plain call: the twin of :meth:`startup`.

        Returns:
            The function.
        """
        return self._register_hook("startup", function, name)

    def merge(self, *others: Union["App[Any]", AppRegistry]) -> "App[Ctx]":
        """Take what other apps or registries declare into this app, in place.

        Declare parts of an app apart from each other, and bring them together here::

            app = App("microscope").merge(stage, camera)

        It takes what they hold now: what is declared on them afterwards does not
        follow. Each part's actions keep the ``effects`` they were declared with, this
        app's default only reaches what is declared on it. Clashing names are refused.

        Args:
            others: The apps or registries to take. They are not changed.

        Returns:
            This app.
        """
        for other in others:
            self.registry.merge(_registry_of(other))
        return self

    @overload
    def lifecycle(self, function: F, /) -> F: ...

    @overload
    def lifecycle(self, /, *, name: Optional[str] = None) -> Callable[[F], F]: ...

    def lifecycle(
        self, function: Optional[F] = None, /, *, name: Optional[str] = None
    ) -> Union[F, Callable[[F], F]]:
        """Set something up and tear it down in one async generator: ``@app.lifecycle``.

        What it yields sets up the app's states and contexts, as a startup hook's return
        does. What follows the yield runs when the app stops providing, after the shutdown
        hooks, so ``async with`` works across the app's whole run::

            @app.lifecycle
            async def mikro(settings: Settings) -> AsyncIterator[Mikro]:
                async with connect(settings) as client:
                    yield client

        It runs in a task of its own, so what it enters is left in the same task.

        Args:
            function: The function, when used bare as ``@app.lifecycle``.
            name: The hook's name. Defaults to the function name.

        Returns:
            The function, or, with options, a decorator returning it.
        """
        return self._hook("lifecycle", function, name)

    def register_lifecycle(self, function: F, /, *, name: Optional[str] = None) -> F:
        """Set up and tear down in one async generator, as a plain call: the twin of :meth:`lifecycle`.

        Returns:
            The function.
        """
        return self._register_hook("lifecycle", function, name)

    @overload
    def shutdown(self, function: F, /) -> F: ...

    @overload
    def shutdown(self, /, *, name: Optional[str] = None) -> Callable[[F], F]: ...

    def shutdown(
        self, function: Optional[F] = None, /, *, name: Optional[str] = None
    ) -> Union[F, Callable[[F], F]]:
        """Run a function when the app stops providing: ``@app.shutdown``.

        Args:
            function: The function, when used bare as ``@app.shutdown``.
            name: The hook's name. Defaults to the function name.

        Returns:
            The function, or, with options, a decorator returning it.
        """
        return self._hook("shutdown", function, name)

    def register_shutdown(self, function: F, /, *, name: Optional[str] = None) -> F:
        """Run a function when the app stops providing, as a plain call: the twin of :meth:`shutdown`.

        Returns:
            The function.
        """
        return self._register_hook("shutdown", function, name)

    @overload
    def background(self, function: F, /) -> F: ...

    @overload
    def background(self, /, *, name: Optional[str] = None) -> Callable[[F], F]: ...

    def background(
        self, function: Optional[F] = None, /, *, name: Optional[str] = None
    ) -> Union[F, Callable[[F], F]]:
        """Run a function in the background while the app provides: ``@app.background``.

        Args:
            function: The function, when used bare as ``@app.background``.
            name: The task's name. Defaults to the function name.

        Returns:
            The function, or, with options, a decorator returning it.
        """
        return self._hook("background", function, name)

    def register_background(self, function: F, /, *, name: Optional[str] = None) -> F:
        """Run a function in the background while the app provides, as a plain call: the twin of :meth:`background`.

        Returns:
            The function.
        """
        return self._register_hook("background", function, name)

    def blok(
        self,
        name: str,
        component: Union[str, ComponentNodeInput],
        description: Optional[str] = None,
        *,
        locals: Optional[Mapping[str, Union[Local[object], JSONSerializable]]] = None,
        demo: Optional[Union[BlokDemoInput, Mapping[str, JSONSerializable]]] = None,
        queries: Optional[Mapping[str, Query]] = None,
        subscriptions: Optional[Mapping[str, Subscription]] = None,
        catalogs: Optional[Sequence[str]] = None,
        module: Optional[str] = None,
        default: bool = False,
        for_model: Optional[str] = None,
        for_node: Optional[str] = None,
        args: Optional[Mapping[str, object]] = None,
        mode: BlokCheckMode = "warning",
    ) -> None:
        r"""Declare a blok of this app's agent (blok language v2): ``app.blok("monitor", "<Html><Card/></Html>")``.

        The tree reads the agent as ``self``: ``self.<state>.<field>``,
        ``self.tasks.<action>``, ``self.assets.<name>``, and calls it as
        ``self.<action>(name: value) into <record>``. What it reads of ``self``
        becomes its one dependency when the agent is built. It is checked now,
        by the spec's validator, against the language and its catalog: an error
        raises, a warning is a :class:`~arkitekt_spec.declare.catalogs.CatalogWarning`.

        Args:
            name: The blok's name.
            component: The component tree, as v2 BSX or already parsed. Its root
                names the context: ``<Html>`` for a panel, ``<Scene>`` for a full 3D
                view, ``<AgentLogo>`` for the app's logo or ``<ActionLogo>`` for an
                action's. An ``<Overlay>`` belongs to an action (``bloks=``).
            description: What the blok shows.
            locals: Its form state, written only through ``bind`` on a control
                (``<Input bind={iterations} />``) and read bare in a call:
                ``{"iterations": Local(15, persist=True)}``. A local is a port, and
                ``Local()`` is usually enough: its kind comes, in order, from a type
                (``Local[float]()``, ``Local(type=list[str])``, a registered structure),
                an action's argument (``Local.like(deconvolve, "iterations")``, which
                copies that port), its default (``Local(15)`` is an INT), the call it is
                passed to whole, or the control bound to it; else it is ANY, checked
                against nothing. A bare value is a local with that default.
            demo: What a preview renders it with, mirroring the roots it reads:
                ``{"deps": {"self": {...}}, "args": {...}, "queries": {...}}``.
                Placeholders for the states of ``self`` it reads when left out.
            queries: Its declared reads, ``queries.<name>``, each a :class:`Query`.
            subscriptions: Its declared streams, ``subscriptions.<name>``, each a
                :class:`Subscription`.
            catalogs: The catalogs it needs (``"ui@1"``, ``"scene@1"``); those its
                components come from when left out.
            module: The module (an app's own unversioned extras) it renders
                against besides its catalogs: the Orkestrator's when left out, or
                one this app declared with :meth:`ui_catalog`.
            default: Whether this is the app's default blok for its context.
                Declaring another default for the same context replaces it.
            for_model: The model (``"sha256:..."``) this blok decorates: a viewer
                showing that model offers it where ``for_node`` is clicked. Html
                bloks only.
            for_node: The node of ``for_model`` to attach to; the model's root
                when left out.
            args: The items the blok is opened for, typed like an action's
                arguments (``{"dataset": ArrayDataset}``) and read as
                ``args.dataset``. Html bloks only.
            mode: ``"warning"`` (the default) warns about a catalog finding,
                ``"strict"`` refuses it.

        Raises:
            ValueError: If the BSX does not parse or the tree breaks a rule of the
                language (a :class:`~arkitekt_spec.blok.vocabulary.BlokError` with its
                code), or the declaration contradicts itself.
        """
        self.registry.register_blok(
            name,
            component,
            description=description,
            locals=locals,
            demo=demo,
            queries=queries,
            subscriptions=subscriptions,
            catalogs=catalogs,
            module=module,
            default=default,
            for_model=for_model,
            for_node=for_node,
            args=args,
            mode=mode,
        )

    def register_asset(
        self,
        name: str,
        path: Optional[Union[str, Path]] = None,
        kind: Optional[AssetKind] = None,
        *,
        source: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> None:
        """Register a file the app uses, under the name its bloks call it by.

        A blok names it as ``self.assets.<name>``: the model of a scene blok, an
        image in a panel::

            app.register_asset("scope", "models/scope.glb")
            app.register_asset("logo", "art/logo.png")

            app.blok("view", '<Scene><Model src={self.assets.scope} /></Scene>')
            app.blok("panel", '<Html><Image src={self.assets.logo} /></Html>')

        When the app runs, a file the server does not hold yet is uploaded. The
        server checks it against its hash and the rules of its kind; one it
        refuses is logged and the app runs on.

        A file too large to ship with the app is named by where it is published
        and the hash of its bytes instead::

            app.register_asset(
                "robot",
                source="https://vendor.example/ur5.glb",
                ref="sha256:9f2c…",
            )

        The app never fetches or uploads that one. Where it is shown, an admin of
        the organization is offered to add it: their client fetches it from the
        source, and the server holds it to the same hash and rules.

        Args:
            name: What bloks call the asset. An identifier, unique within the app.
            path: The file, relative to the app's directory: where the file that
                constructs the app is, unless the app was given a ``root``. A
                path that leaves that directory is refused, so that an asset is
                always part of what the app is packaged from.
            kind: What the file is. Told from the extension when left out
                (``.glb`` is a 3D model; ``.png``, ``.jpg``, ``.jpeg`` and
                ``.webp`` are images).
            source: The https URL the file is fetched from, given instead of
                ``path``.
            ref: The hash of the file at ``source``: ``"sha256:"`` and the hex
                SHA-256 of its exact bytes. Required with ``source``.
        """
        self.registry.register_asset(name, path, kind, source=source, ref=ref)

    def ui_catalog(
        self,
        name: str,
        components: Optional[Sequence[ComponentSpec]] = None,
        operations: Optional[Sequence[OperationSpec]] = None,
        description: Optional[str] = None,
    ) -> None:
        """Declare a module: what a renderer draws and evaluates beyond the spec's catalogs.

        Bloks naming it as their ``module`` are validated against it offline, when they
        are declared, rather than only once the server sees them. The same declaration
        is what a UI app uploads with ``registerModule``.

        Unlike the other declarations this offers nothing and needs no agent: a UI
        app registering its module, or an author declaring one purely to validate,
        should not be made to serve.

        Args:
            name: The module's name, as bloks name it (``module="electron"``).
            components: The components the UI can render.
            operations: Pure operations the UI can evaluate, extending the base catalog.
            description: What the module is.

        Raises:
            ValueError: If it redefines a base operation, or a different module is
                already declared under ``name``.
        """
        self.registry.declare_ui_catalog(
            name,
            components=components,
            operations=operations,
            description=description,
        )

    def declare(
        self,
        app: Optional[str] = None,
        *,
        auto_resolvable: bool = False,
        min: Optional[int] = None,
        max: Optional[int] = None,
        version: Optional[str] = None,
    ) -> Callable[[C], C]:
        """Declare a protocol: what this app demands of another app. ``@app.declare(app="lab")``.

        The class's public methods become action demands and its public
        annotated attributes state demands (each annotated with a class whose
        annotations are the state's fields), with their ports built now against
        this app's structures. The class is
        returned unchanged; declaring it on a second app builds that app's own.
        An action parameter annotated with it is handed a proxy that calls the
        remote agent::

            @app.declare(app="lab")
            class Camera(Protocol):
                async def snap(self, exposure_ms: float) -> bytes: ...

            @app.action
            def measure(camera: Camera) -> float:
                return len(camera.snap(10.0))

        Args:
            app: The remote app the protocol is directed at, if any.
            auto_resolvable: Whether any matching agent may be assigned
                automatically.
            min: Minimum viable number of matching agents.
            max: Maximum viable number of matching agents.
            version: The protocol's version.

        Returns:
            A class decorator returning the class.

        Raises:
            DefinitionError: If a demand names a class this app cannot make a
                port of -- usually a structure of a service it does not declare.
        """
        return self.registry.declare(
            app, auto_resolvable=auto_resolvable, min=min, max=max, version=version
        )

    def interactions(self, cls: C, /) -> C:
        """Declare an interactions protocol: the bloks an action asks a person through or
        shows them. ``@app.interactions``.

        Each method decorated with :func:`~arkitekt_spec.declare.interactions.ask` is one ask:
        its parameters are the blok's args, its return what an answer holds. Each decorated
        with :func:`~arkitekt_spec.declare.interactions.inform` is one inform: its parameters
        are the blok's args, and it returns nothing. The docstring is what either is listed
        as. Their ports are built and their bloks checked now. An action parameter annotated
        with the class is handed a proxy, and the action declares each, so the server shows
        them without ``dynamic_asks``/``dynamic_informs``::

            @app.interactions
            class UI(Protocol):
                @ask('<Html><Button label="Go" onClick={task.answer(values: {ok: true})} /></Html>')
                def go(self, name: str) -> Annotated[bool, Key("ok")]:
                    \"\"\"Go on?\"\"\"

                @inform("<Html><Text text={args.name} /></Html>")
                def started(self, name: str) -> None:
                    \"\"\"Started.\"\"\"

            @app.action
            def run(name: str, ui: UI) -> str:
                ui.go(name=name)        # DismissedError when dismissed
                ui.started(name=name)   # shown; the task goes on
                return name

        Returns:
            The class, unchanged.

        Raises:
            DefinitionError: If a public method is neither an ask nor an inform, or its blok breaks a rule.
        """
        self.registry.register_interactions(cls)
        return cls

    def register_interactions(self, cls: type[Any], /) -> None:
        """Declare an interactions protocol, as a plain call: the twin of :meth:`interactions`."""
        self.registry.register_interactions(cls)

    def register_protocol(
        self,
        cls: C,
        /,
        app: Optional[str] = None,
        *,
        auto_resolvable: bool = False,
        min: Optional[int] = None,
        max: Optional[int] = None,
        version: Optional[str] = None,
    ) -> C:
        """Declare a protocol, as a plain call: the twin of :meth:`declare`.

        Returns:
            The class, unchanged.

        Raises:
            DefinitionError: If a demand names a class this app cannot make a
                port of -- usually a structure of a service it does not declare.
        """
        return self.declare(
            app, auto_resolvable=auto_resolvable, min=min, max=max, version=version
        )(cls)

    def register_structure(
        self,
        cls: type,
        identifier: str,
        *,
        expand: Callable[..., Any],
        shrink: Optional[Callable[..., Any]] = None,
        description: Optional[str] = None,
        default_widget: Optional[AssignWidgetInput] = None,
        describe: Optional[Callable[[Any], Mapping[str, Any]]] = None,
    ) -> None:
        """Declare a type that travels by id, with your own way of fetching it back.

        For a type a *shared library* defines -- one that both the sending and the
        receiving app know, because both import it. A service's own types do not
        go through here: those are :class:`~arkitekt_spec.declare.structures.description.StructureDescription`
        in the service's ``structures=``, and are expanded by that service's client.

        The expander says what it needs by annotation, the same way an action
        does, and a run hands it exactly those::

            async def expand_thing(id: str, mikro: Mikro) -> Thing:
                return Thing(await mikro.aget_file(id))

            app.register_structure(Thing, "@lib/thing", expand=expand_thing)

        It must be a named function with annotated parameters: a lambda has no
        annotations, so there would be nothing to read.

        Unlike an action, this does **not** declare the services it names. Whether
        a declared service can build them is checked when the app is inspected or
        run, together with everything else -- see :meth:`snapshot`.

        Args:
            cls: The class that travels.
            identifier: What it travels as, ``@package/key``. A contract with
                every other app that handles this type.
            expand: Turns an id back into the object. Its first parameter is the
                id; any others are clients, by annotation.
            shrink: Turns the object into its id. Defaults to reading ``.id``.
            description: What it is, for the UI.
            default_widget: The widget a user picks one with.
            describe: Computes an object's descriptors, a flat ``{key: value}``.
                A run tests them against a port's ``Requires`` when one comes in
                and its ``Provides`` when one goes out, and fails the task on a
                mismatch. A key it does not return is not tested.

        Raises:
            StructureDefinitionError: If the identifier is not ``@package/key``,
                or the expander's parameters cannot be read or are not clients.
        """
        self.registry.structure_registry.register_as_structure(
            cls,
            identifier=identifier,
            aexpand=expand,
            ashrink=shrink or id_shrink,
            description=description,
            default_widget=default_widget,
            describe=describe,
        )

    def memory_structure(
        self, cls: type, identifier: Optional[str] = None, description: Optional[str] = None
    ) -> None:
        """Declare a class whose instances stay on the agent: ``app.memory_structure(np.ndarray)``.

        Nothing is registered automatically, so a port may only name a class the
        app knows: one its services declared, or one declared here.

        Args:
            cls: The class to keep on the agent.
            identifier: What it travels as. Defaults to the class name in the app's
                namespace for a class the app defines (``@myapp/blob``), else in its
                module (``numpy.ndarray`` -> ``@numpy/ndarray``).
            description: What it is, for the UI.
        """
        self.registry.register_memory_structure(cls, identifier=identifier, description=description)
