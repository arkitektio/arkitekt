"""The app: a declaration of what it is and what it offers.

An :class:`App` does no I/O and holds no connection. It says who it is (identifier,
version, scopes, ...), which services it uses, and what it offers (actions, states,
hooks, bloks). Running it is someone else's job: :func:`arkitekt.run` provides it,
:func:`arkitekt.connect` only connects, and each of them builds a fresh
:class:`~arkitekt.runtime.Runtime` holding everything stateful.

```python
from arkitekt import App, run
from mikro import Mikro, mikro_service

app = App("my-app", version="0.1.0")
app.service(mikro_service)

@app.action
def segment(image: ArrayDataset, mikro: Mikro) -> ArrayDataset: ...

if __name__ == "__main__":
    run(app)
```

Because nothing here is stateful, one app can be run any number of times, and
concurrently: each run takes its own snapshot of the registry.
"""

import inspect
import logging
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
    TypeVar,
    Union,
    cast,
    dataclass_transform,
    overload,
)

from arkitekt_spec.actions import (
    AgentDependencyInput,
    AssignWidgetInput,
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
from arkitekt_spec.declare.catalogs import ComponentSpec, OperationSpec
from arkitekt_spec.declare.coercible_types import OptimisticCoercible
from arkitekt_spec.declare.provider import Provider
from arkitekt_spec.declare.register import WrappedFunction
from arkitekt_spec.declare.service import Service
from arkitekt_spec.declare.structures.convert import model_identifier
from arkitekt_spec.declare.structures.model import model_field
from arkitekt_spec.declare.structures.utils import id_shrink
from fakts.models import Manifest, PublicSource, Requirement

from arkitekt.app.snapshot import RunSnapshot

logger = logging.getLogger(__name__)

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


def _caller_module_name(depth: int = 2) -> str:
    """Name the module some caller up the stack is defined in.

    Args:
        depth: How many frames up the caller is; 2 is the caller of the function
            that calls this one.

    Returns:
        That module's file name without ``.py``, used as a default identifier.
    """
    frame = inspect.stack()[depth]
    # Path, not "/": on Windows a frame's filename uses backslashes.
    return Path(frame.filename).stem


class App(Generic[Ctx]):
    """What an app is and what it offers. Pure declaration: no I/O, no clients.

    Args:
        identifier: The app's globally unique identifier. Defaults to the name of
            the file that constructs it.
        version: The app's version.
        description: What the app is, in a sentence. It goes into the manifest
            and, from there, onto the agent that provides the app -- shown
            beside its name, which is what tells two agents of the same app
            apart from what they are.
        logo: A public http url of the app's logo.
        scopes: The scopes the app requests. Defaults to ``["openid"]``.
        author: Who wrote the app. Used when packaging it.
        public_sources: Public sources the app announces in its manifest.
        services: The services the app uses (``[mikro_service]``). The same as
            calling :meth:`service` for each.
        providers: The provider that serves what the app offers. Without one,
            ``run(app)`` serves it through rekuest's.
        registry: The registry to declare into. A fresh one by default.
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
        app_context: Optional[type[Ctx]] = None,
        effects: Optional[Effects] = None,
    ) -> None:
        self.identifier: str = identifier or _caller_module_name()
        self.version = version
        self.description = description
        self.logo = logo
        self.scopes: List[str] = list(scopes) if scopes else ["openid"]
        self.author = author
        self.public_sources: List[PublicSource] = list(public_sources or [])
        self.registry: AppRegistry = registry if registry is not None else AppRegistry()
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
            update={"requirements": _requirements_of(registry)}
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
        effects: Optional[Effects] = None,
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
        effects: Optional[Effects] = None,
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
            effects: What running it again would do to the world. Informational:
                shown to whoever decides about a lost task. Defaults to the app's
                ``effects``.

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
                effects=effects,
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
        effects: Optional[Effects] = None,
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
                effects=effects,
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
        effects: Optional[Effects] = None,
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
        effects: Optional[Effects] = None,
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
            effects: What running it again would do to the world. Informational:
                shown to whoever decides about a lost task. Defaults to the app's
                ``effects``.

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
                effects=effects,
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
        effects: Optional[Effects] = None,
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
                effects=effects,
                execution=Execution.WORKFLOW,
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
    ) -> C: ...

    @overload
    def state(
        self,
        /,
        *,
        name: Optional[str] = None,
        required_locks: Optional[List[str]] = None,
    ) -> Callable[[C], C]: ...

    @dataclass_transform(field_specifiers=(model_field,))
    def state(
        self,
        cls: Optional[C] = None,
        /,
        *,
        name: Optional[str] = None,
        required_locks: Optional[List[str]] = None,
    ) -> Union[C, Callable[[C], C]]:
        """Declare a class as a state other apps can observe: ``@app.state``.

        Args:
            cls: The class, when used bare as ``@app.state``.
            name: The interface the state is offered at. Defaults to the class name.
            required_locks: Locks an action must hold to change the state.

        Returns:
            The class, or, with options, a decorator returning it.
        """

        def declare(cls: C) -> C:
            return self.register_state(cls, name=name, required_locks=required_locks)

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
    ) -> C:
        """Declare a class as a state, as a plain call: the twin of :meth:`state`.

        Returns:
            The class.
        """
        self.registry.state(cls, name=name, required_locks=required_locks)
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
                identifier=identifier or model_identifier(self.identifier, cls),
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
        demo_state: Optional[Dict[str, Any]] = None,
        dependencies: Optional[
            Union[Mapping[str, type], Sequence[AgentDependencyInput]]
        ] = None,
        catalog: Optional[str] = None,
        local_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Declare a blok, a UI component tree: ``app.blok("monitor", "<Card/>")``.

        Args:
            name: The blok's name.
            component: The component tree, as BSX or already parsed.
            description: What the blok shows.
            demo_state: State to render the blok with when there is none.
            dependencies: Other apps' actions and states the blok uses: the
                protocol classes this app :meth:`declare`\ d, by the key the
                tree uses (``{"camera": CameraProtocol}``). This app's own are
                inferred.
            catalog: The UI catalog the blok renders against. When this app has
                declared it with :meth:`ui_catalog`, the tree's components, props
                and util operations are checked against it now.
            local_state: The blok's own UI state and its initial values, e.g.
                ``{"form": {"iterations": 15}}``: roots the tree binds controls
                to (``bind="form.iterations"``) and reads back in a call
                (``@self.run(iterations=form.iterations)``).

        Raises:
            ValueError: If ``name`` is empty, a declared catalog rejects the tree,
                or a ``local_state`` key is reserved or names a dependency.
        """
        self.registry.register_blok(
            name,
            component,
            description=description,
            demo_state=demo_state,
            dependencies=dependencies,
            catalog=catalog,
            local_state=local_state,
        )

    def ui_catalog(
        self,
        name: str,
        components: Optional[Sequence[ComponentSpec]] = None,
        operations: Optional[Sequence[OperationSpec]] = None,
        description: Optional[str] = None,
    ) -> None:
        """Declare a UI catalog: what a renderer can draw and evaluate.

        Bloks naming it are validated against it offline, when they are declared,
        rather than only once the server sees them. The same declaration is what a
        UI app uploads with ``registerUiCatalog``.

        Unlike the other declarations this offers nothing and needs no agent: a UI
        app registering its catalog, or an author declaring one purely to validate,
        should not be made to serve.

        Args:
            name: The catalog's name, as bloks refer to it.
            components: The components the UI can render.
            operations: Pure operations the UI can evaluate, extending the base catalog.
            description: What the catalog is.

        Raises:
            ValueError: If it redefines a base operation, or a different catalog is
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
        )

    def memory_structure(
        self, cls: type, identifier: Optional[str] = None, description: Optional[str] = None
    ) -> None:
        """Declare a class whose instances stay on the agent: ``app.memory_structure(np.ndarray)``.

        Nothing is registered automatically, so a port may only name a class the
        app knows: one its services declared, or one declared here.

        Args:
            cls: The class to keep on the agent.
            identifier: What it travels as. Defaults to one derived from the class
                (``numpy.ndarray`` -> ``@numpy/ndarray``).
            description: What it is, for the UI.
        """
        self.registry.register_memory_structure(cls, identifier=identifier, description=description)
