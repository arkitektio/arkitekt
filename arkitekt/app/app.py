"""The app: a declaration of what it is and what it offers.

An :class:`App` does no I/O and holds no connection. It says who it is (identifier,
version, scopes, ...) and what it offers (actions, states, hooks, bloks); the clients
it uses are found in the annotations of what it offers. Running it is someone
else's job: :func:`arkitekt.run` provides it, :func:`arkitekt.connect` only
connects, and each builds a fresh :class:`~arkitekt.runtime.Runtime`.

```python
from arkitekt import App, run
from mikro import Mikro
from mikro.api.schema import Image

app = App("my-app", version="0.1.0")

@app.action
def segment(image: Image, mikro: Mikro) -> Image: ...

if __name__ == "__main__":
    run(app)
```

Declaring records; nothing is built until the app is assembled
(:meth:`App.declaration`), so declaration order does not matter and every problem
is reported at once.
"""

import inspect
import logging
import os
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, is_dataclass
from pathlib import Path
from typing import (
    Any,
    Generic,
    Literal,
    ParamSpec,
    TypeVar,
    dataclass_transform,
    overload,
)

from arkitekt_spec.actions import (
    AssetKind,
    AssignWidgetInput,
    BlokDemoInput,
    ComponentNodeInput,
    Effects,
    Execution,
    PortGroupInput,
    TestTargetInput,
    ValidatorInput,
)
from arkitekt_spec.declare import markers
from arkitekt_spec.declare.actors.policy import KEEP, DisconnectPolicy
from arkitekt_spec.declare.actors.types import Actifier
from arkitekt_spec.declare.app import AppRegistry, check_app_context
from arkitekt_spec.declare.assemble import assemble
from arkitekt_spec.declare.blok.action import ActionBloks
from arkitekt_spec.declare.bundle import Bundle
from arkitekt_spec.declare.catalogs import BlokCheckMode, ComponentSpec, OperationSpec
from arkitekt_spec.declare.coercible_types import OptimisticCoercible
from arkitekt_spec.declare.provider import Provider
from arkitekt_spec.declare.register import WrappedFunction
from arkitekt_spec.declare.structures.convert import AppNamespace, source_root
from arkitekt_spec.declare.structures.model import ensure_model_dataclass, model_field
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


def _requirements_of(registry: AppRegistry) -> list[Requirement]:
    """What an assembled app's clients and provider require, one per key, sorted."""
    merged: dict[str, Requirement] = {}
    for group in (
        *(client.get_requirements() for client in registry.clients.values()),
        registry.provider.get_requirements() if registry.provider else [],
    ):
        for requirement in group:
            merged.setdefault(requirement.key, requirement)
    return sorted(merged.values(), key=lambda requirement: requirement.key)


#: The scope every app asks for: it logs a user in.
BASE_SCOPES = ("openid",)


def _scopes_of(registry: AppRegistry, asked: Iterable[str] = ()) -> list[str]:
    """What an assembled app asks for: its own, what each client needs, and what its
    actions' dynamic asks and calls need."""
    return sorted(
        {
            *BASE_SCOPES,
            *asked,
            *(
                scope
                for client in registry.clients.values()
                for scope in client.get_scopes()
            ),
            *registry.get_scopes(),
        }
    )


def _caller(depth: int = 2) -> tuple[Path, str | None]:
    """The file and module some caller up the stack is defined in (2: the caller's caller)."""
    frame = inspect.stack()[depth].frame
    name = frame.f_globals.get("__name__")
    # Path, not "/": on Windows a frame's filename uses backslashes.
    return Path(frame.f_code.co_filename), name if isinstance(name, str) else None


def _app_namespace(identifier: str, caller: tuple[Path, str | None]) -> AppNamespace:
    """The namespace of an app named ``identifier`` constructed by ``caller`` (from
    :func:`_caller`): what counts as the app's own source."""
    constructed_in, module = caller
    return AppNamespace(
        identifier=identifier, root=source_root(constructed_in), module=module
    )


def _app_root(constructed_in: Path) -> Path:
    """The directory of an app constructed in ``constructed_in``; the working one for a console."""
    return constructed_in.resolve().parent if constructed_in.is_file() else Path.cwd()


class App(Bundle, Generic[Ctx]):
    """What an app is and what it offers. Pure declaration: no I/O, no clients.

    Args:
        identifier: The app's globally unique identifier. Defaults to the name of
            the file that constructs it. It also namespaces the identifiers derived
            for the enums, memory structures and models the app defines itself
            (``@<identifier>/...``).
        version: The app's version. ``ARKITEKT_APP_VERSION`` (set in an image built
            from a branch) wins.
        description: What the app is, in a sentence: shown beside its agent's name.
        logo: A public http url of the app's logo.
        scopes: Scopes beyond what its clients need (those, and ``openid``, are
            asked for anyway).
        author: Who wrote the app. Used when packaging it.
        public_sources: Public sources the app announces in its manifest.
        clients: ``@client`` classes the app uses although no annotation names them
            (a blok's query, a script's calls).
        include: Bundles whose actions the app offers too (``fluss_actions``).
        provider: What serves the app's offerings. Without one, ``run(app)`` serves
            it through rekuest's.
        root: The app's directory, which asset paths are relative to. Defaults to
            the directory of the file that constructs the app.
        app_context: The class of the app context, what a run hands the agent
            (``run(app, context=Config(...))``). An app declaring one is
            ``App[Config]`` and every run must pass an instance.
        effects: What running an action again would do, for the actions that don't
            say themselves. Informational.

    Raises:
        TypeError: If a client is not a ``@client`` class, or a provider not a provider.
    """

    @overload
    def __init__(
        self: "App[None]",
        identifier: str | None = None,
        version: str = "0.0.1",
        *,
        description: str | None = None,
        logo: str | None = None,
        scopes: list[str] | None = None,
        author: str | None = None,
        public_sources: list[PublicSource] | None = None,
        clients: Sequence[type] = (),
        include: Sequence[Bundle] = (),
        provider: Provider[Any] | None = None,
        root: str | Path | None = None,
        app_context: None = None,
        effects: Effects | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        identifier: str | None = None,
        version: str = "0.0.1",
        *,
        description: str | None = None,
        logo: str | None = None,
        scopes: list[str] | None = None,
        author: str | None = None,
        public_sources: list[PublicSource] | None = None,
        clients: Sequence[type] = (),
        include: Sequence[Bundle] = (),
        provider: Provider[Any] | None = None,
        root: str | Path | None = None,
        app_context: type[Ctx],
        effects: Effects | None = None,
    ) -> None: ...

    def __init__(
        self,
        identifier: str | None = None,
        version: str = "0.0.1",
        *,
        description: str | None = None,
        logo: str | None = None,
        scopes: list[str] | None = None,
        author: str | None = None,
        public_sources: list[PublicSource] | None = None,
        clients: Sequence[type] = (),
        include: Sequence[Bundle] = (),
        provider: Provider[Any] | None = None,
        root: str | Path | None = None,
        app_context: type[Ctx] | None = None,
        effects: Effects | None = None,
    ) -> None:
        super().__init__()
        caller = _caller()
        constructed_in = caller[0]
        self.identifier: str = identifier or constructed_in.stem
        self.version = os.environ.get(VERSION_ENV) or version
        self.description = description
        self.logo = logo
        # What the app asks for beyond what its clients need (see `scopes`).
        self.asked_scopes: list[str] = list(scopes or [])
        self.author = author
        self.public_sources: list[PublicSource] = list(public_sources or [])
        # What a derived identifier is namespaced by: the app for a class it defines
        # itself, never the module that class happens to be in. A wrapper
        # constructing the app for its caller (QtApp, connect(Mikro)) sets it again.
        self.namespace: AppNamespace = _app_namespace(self.identifier, caller)
        self.root: Path = (
            Path(root).resolve() if root is not None else _app_root(constructed_in)
        )
        self._app_context: type[Ctx] | None = app_context
        self.default_effects: Effects | None = effects
        if provider is not None and not isinstance(provider, Provider):
            raise TypeError(
                f"{provider!r} is not a provider: pass what a package exports, e.g. "
                "`from rekuest.arkitekt import rekuest_provider`."
            )
        self.provider: Provider[Any] | None = provider
        self.register_client(*clients)
        self.include(*include)
        self._assembled: dict[object, tuple[object, AppRegistry]] = {}

    @property
    def app_context(self) -> type[Ctx] | None:
        """The class a run's ``context=`` must be an instance of, or ``None``."""
        return self._app_context

    def require_app_context(self, value: object, *, whose: str | None = None) -> None:
        """Refuse a run whose ``context=`` does not fit what this app declares.

        Raises:
            AppContextError: If it does not.
        """
        check_app_context(
            self._app_context, value, whose=whose or f"App {self.identifier!r}"
        )

    def __repr__(self) -> str:
        return f"App({self.identifier!r}, version={self.version!r})"

    # ------------------------------------------------------------------ #
    # Assembly                                                           #
    # ------------------------------------------------------------------ #

    def declaration(self, provider: Provider[Any] | None = None) -> AppRegistry:
        """What this app declares, assembled: every client, structure, action, hook and blok.

        Assembled once per change: declaring something more, or a class being
        marked, assembles it again.

        Args:
            provider: The provider a run serves it through, when the app names
                none (rekuest's, for ``run(app)``).

        Raises:
            AppDeclarationError: Every problem found, each with where it was declared.
        """
        provider = self.provider or provider
        key = (self.fingerprint(), markers.EPOCH, self.namespace, self.root)
        cached = self._assembled.get(id(provider))
        if cached is not None and cached[0] == key:
            return cached[1]
        registry = assemble(
            self,
            namespace=self.namespace,
            root=self.root,
            app_context=self._app_context,
            default_effects=self.default_effects,
            provider=provider,
        )
        self._assembled[id(provider)] = (key, registry)
        return registry

    @property
    def registry(self) -> AppRegistry:
        """This app's declaration, assembled (:meth:`declaration`). Read it; declare on the app."""
        return self.declaration()

    # ------------------------------------------------------------------ #
    # Identity                                                           #
    # ------------------------------------------------------------------ #

    @property
    def scopes(self) -> list[str]:
        """What this app asks to be allowed to do: what its clients need, and its own."""
        return _scopes_of(self.declaration(), self.asked_scopes)

    @property
    def requirements(self) -> list[Requirement]:
        """What this app requires of a deployment: what its clients (and provider) need.

        A run adds what its provider requires when the app names none; see :meth:`snapshot`.
        """
        return _requirements_of(self.declaration())

    @property
    def manifest(self) -> Manifest:
        """What this app tells the server it is. Carries no device id: a run adds it."""
        from arkitekt.app.spec import app_manifest

        return Manifest(
            **dict(app_manifest(self)),
            requirements=self.requirements,
            public_sources=list(self.public_sources),
        )

    def snapshot(
        self, device_id: str | None = None, provider: "Provider[Any] | None" = None
    ) -> "RunSnapshot":
        """Take what a run of this app would serve, without connecting.

        Args:
            device_id: The device the run happens on, written into the manifest.
            provider: The provider the run builds its agent from, when the app names
                none: taken in with the clients it uses.

        Returns:
            The snapshot: validated, frozen, with no clients bound.

        Raises:
            AppDeclarationError: If the app cannot be assembled.
        """
        registry = self.declaration(provider)
        manifest = self.manifest.model_copy(
            update={
                "requirements": _requirements_of(registry),
                "scopes": _scopes_of(registry, self.asked_scopes),
            }
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
        name: str | None = None,
        description: str | None = None,
        actifier: Actifier | None = None,
        interface: str | None = None,
        stateful: bool = False,
        widgets: dict[str, AssignWidgetInput] | None = None,
        collections: list[str] | None = None,
        port_groups: list[PortGroupInput] | None = None,
        is_test_for: list[TestTargetInput] | None = None,
        validators: dict[str, list[ValidatorInput]] | None = None,
        optimistics: list[OptimisticCoercible] | None = None,
        in_process: bool = False,
        locks: list[str] | None = None,
        concurrency: Literal["parallel", "serial"] = "serial",
        policy: DisconnectPolicy = KEEP,
        version: str | None = None,
        catalogs: list[str] | None = None,
        protocols: list[str] | None = None,
        effects: Effects | None = None,
        logo: str | ComponentNodeInput | None = None,
        bloks: ActionBloks | None = None,
        dynamic_asks: bool = False,
        dynamic_calls: bool = False,
        dynamic_informs: bool = False,
        estimated_runtime: str | None = None,
        estimated_runtime_ui: str | None = None,
    ) -> Callable[[Callable[P, R]], WrappedFunction[P, R]]: ...

    def action(
        self,
        function: Callable[P, R] | None = None,
        /,
        *,
        name: str | None = None,
        description: str | None = None,
        actifier: Actifier | None = None,
        interface: str | None = None,
        stateful: bool = False,
        widgets: dict[str, AssignWidgetInput] | None = None,
        collections: list[str] | None = None,
        port_groups: list[PortGroupInput] | None = None,
        is_test_for: list[TestTargetInput] | None = None,
        validators: dict[str, list[ValidatorInput]] | None = None,
        optimistics: list[OptimisticCoercible] | None = None,
        in_process: bool = False,
        locks: list[str] | None = None,
        concurrency: Literal["parallel", "serial"] = "serial",
        policy: DisconnectPolicy = KEEP,
        version: str | None = None,
        catalogs: list[str] | None = None,
        protocols: list[str] | None = None,
        effects: Effects | None = None,
        logo: str | ComponentNodeInput | None = None,
        bloks: ActionBloks | None = None,
        dynamic_asks: bool = False,
        dynamic_calls: bool = False,
        dynamic_informs: bool = False,
        estimated_runtime: str | None = None,
        estimated_runtime_ui: str | None = None,
    ) -> WrappedFunction[P, R] | Callable[[Callable[P, R]], WrappedFunction[P, R]]:
        """Offer a function as an action: ``@app.action`` or ``@app.action(name=...)``.

        Parameters annotated with a client class (``mikro: Mikro``) or with
        :class:`~arkitekt_spec.declare.task.Task` are injected rather than becoming ports;
        the client is then used by the app.

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
            is_test_for: Actions this one tests.
            validators: Input validation rules per argument.
            optimistics: Optimistic outputs.
            in_process: Run in the event loop instead of a worker thread.
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
                this app declares (``app.blok(name, '<Blok kind="action" context="logo">...</Blok>')``),
                or a tree of its own (``bsx(...)``). Without one, a client shows the app's
                default logo.
            bloks: The action's own bloks, one per kind and context, each a ``<Blok>``:
                ``kind="action"`` for how a client shows a run (``context="panel"`` a task
                panel; ``context="scene"`` holding a ``<Space room="room:lab">`` that places
                the run's dependencies in a room whose layout is shared, its
                ``<Placed dep="robot">`` drawing the agent the run got for that parameter
                with its own scene blok), ``kind="assign"`` for starting one (shown before
                there is a task; ``<args />`` places the argument form, ``assign.start()``
                starts the run). A bare tree, or an ``ActionBlok`` for a demo and a
                description; one needs no list.
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

        Nothing is built here: a parameter that cannot become a port is reported
        when the app is assembled (:class:`~arkitekt_spec.declare.errors.AppDeclarationError`).
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
                is_test_for=is_test_for,
                validators=validators,
                optimistics=optimistics,
                in_process=in_process,
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
        name: str | None = None,
        description: str | None = None,
        actifier: Actifier | None = None,
        interface: str | None = None,
        stateful: bool = False,
        widgets: dict[str, AssignWidgetInput] | None = None,
        collections: list[str] | None = None,
        port_groups: list[PortGroupInput] | None = None,
        is_test_for: list[TestTargetInput] | None = None,
        validators: dict[str, list[ValidatorInput]] | None = None,
        optimistics: list[OptimisticCoercible] | None = None,
        in_process: bool = False,
        locks: list[str] | None = None,
        concurrency: Literal["parallel", "serial"] = "serial",
        policy: DisconnectPolicy = KEEP,
        version: str | None = None,
        catalogs: list[str] | None = None,
        protocols: list[str] | None = None,
        effects: Effects | None = None,
        logo: str | ComponentNodeInput | None = None,
        bloks: ActionBloks | None = None,
        dynamic_asks: bool = False,
        dynamic_calls: bool = False,
        dynamic_informs: bool = False,
        estimated_runtime: str | None = None,
        estimated_runtime_ui: str | None = None,
    ) -> WrappedFunction[P, R]:
        """Offer a function as an action, as a plain call: ``app.register_action(function, name=...)``.

        The twin of :meth:`action`, with the same options, for a function that is
        declared somewhere else or offered only under a condition.

        Returns:
            The function, still callable as itself.

        Nothing is built here: a parameter that cannot become a port is reported
        when the app is assembled (:class:`~arkitekt_spec.declare.errors.AppDeclarationError`).
        """
        options = dict(
            name=name,
            description=description,
            actifier=actifier,
            interface=interface,
            stateful=stateful,
            widgets=widgets,
            collections=collections,
            port_groups=port_groups,
            is_test_for=is_test_for,
            validators=validators,
            optimistics=optimistics,
            in_process=in_process,
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
        return self._offer("register_action", function, options)

    @overload
    def workflow(self, function: Callable[P, R], /) -> WrappedFunction[P, R]: ...

    @overload
    def workflow(
        self,
        /,
        *,
        name: str | None = None,
        description: str | None = None,
        actifier: Actifier | None = None,
        interface: str | None = None,
        stateful: bool = False,
        widgets: dict[str, AssignWidgetInput] | None = None,
        collections: list[str] | None = None,
        port_groups: list[PortGroupInput] | None = None,
        is_test_for: list[TestTargetInput] | None = None,
        validators: dict[str, list[ValidatorInput]] | None = None,
        optimistics: list[OptimisticCoercible] | None = None,
        in_process: bool = False,
        locks: list[str] | None = None,
        concurrency: Literal["parallel", "serial"] = "serial",
        policy: DisconnectPolicy = KEEP,
        version: str | None = None,
        catalogs: list[str] | None = None,
        protocols: list[str] | None = None,
        effects: Effects | None = None,
        logo: str | ComponentNodeInput | None = None,
        bloks: ActionBloks | None = None,
        dynamic_asks: bool = False,
        dynamic_calls: bool = False,
        dynamic_informs: bool = False,
        estimated_runtime: str | None = None,
        estimated_runtime_ui: str | None = None,
    ) -> Callable[[Callable[P, R]], WrappedFunction[P, R]]: ...

    def workflow(
        self,
        function: Callable[P, R] | None = None,
        /,
        *,
        name: str | None = None,
        description: str | None = None,
        actifier: Actifier | None = None,
        interface: str | None = None,
        stateful: bool = False,
        widgets: dict[str, AssignWidgetInput] | None = None,
        collections: list[str] | None = None,
        port_groups: list[PortGroupInput] | None = None,
        is_test_for: list[TestTargetInput] | None = None,
        validators: dict[str, list[ValidatorInput]] | None = None,
        optimistics: list[OptimisticCoercible] | None = None,
        in_process: bool = False,
        locks: list[str] | None = None,
        concurrency: Literal["parallel", "serial"] = "serial",
        policy: DisconnectPolicy = KEEP,
        version: str | None = None,
        catalogs: list[str] | None = None,
        protocols: list[str] | None = None,
        effects: Effects | None = None,
        logo: str | ComponentNodeInput | None = None,
        bloks: ActionBloks | None = None,
        dynamic_asks: bool = False,
        dynamic_calls: bool = False,
        dynamic_informs: bool = False,
        estimated_runtime: str | None = None,
        estimated_runtime_ui: str | None = None,
    ) -> WrappedFunction[P, R] | Callable[[Callable[P, R]], WrappedFunction[P, R]]:
        """Offer a workflow: an action that may call other actions. ``@app.workflow``.

        It is called exactly like an action. What differs is what happens when its
        agent dies: it is resumed, not lost. Calls it already made return their
        recorded results instead of running again, and values it took through the
        task (``task.now()``, ``task.record(...)``) come back the same. So its code
        must be deterministic: outside values come in only through calls and the task.

        A step whose own agent dies raises ``AgentLost`` at the call; handle it like
        any exception, or with ``task.retry(...)`` / ``task.hold(...)``.

        Parameters annotated with a client class (``mikro: Mikro``) or with
        :class:`~arkitekt_spec.declare.task.Task` are injected rather than becoming ports;
        the client is then used by the app.

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
            is_test_for: Actions this one tests.
            validators: Input validation rules per argument.
            optimistics: Optimistic outputs.
            in_process: Run in the event loop instead of a worker thread.
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
                this app declares (``app.blok(name, '<Blok kind="action" context="logo">...</Blok>')``),
                or a tree of its own (``bsx(...)``). Without one, a client shows the app's
                default logo.
            bloks: The action's own bloks, one per kind and context, each a ``<Blok>``:
                ``kind="action"`` for how a client shows a run (``context="panel"`` a task
                panel; ``context="scene"`` holding a ``<Space room="room:lab">`` that places
                the run's dependencies in a room whose layout is shared, its
                ``<Placed dep="robot">`` drawing the agent the run got for that parameter
                with its own scene blok), ``kind="assign"`` for starting one (shown before
                there is a task; ``<args />`` places the argument form, ``assign.start()``
                starts the run). A bare tree, or an ``ActionBlok`` for a demo and a
                description; one needs no list.
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

        Nothing is built here: a parameter that cannot become a port is reported
        when the app is assembled (:class:`~arkitekt_spec.declare.errors.AppDeclarationError`).
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
                is_test_for=is_test_for,
                validators=validators,
                optimistics=optimistics,
                in_process=in_process,
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
        name: str | None = None,
        description: str | None = None,
        actifier: Actifier | None = None,
        interface: str | None = None,
        stateful: bool = False,
        widgets: dict[str, AssignWidgetInput] | None = None,
        collections: list[str] | None = None,
        port_groups: list[PortGroupInput] | None = None,
        is_test_for: list[TestTargetInput] | None = None,
        validators: dict[str, list[ValidatorInput]] | None = None,
        optimistics: list[OptimisticCoercible] | None = None,
        in_process: bool = False,
        locks: list[str] | None = None,
        concurrency: Literal["parallel", "serial"] = "serial",
        policy: DisconnectPolicy = KEEP,
        version: str | None = None,
        catalogs: list[str] | None = None,
        protocols: list[str] | None = None,
        effects: Effects | None = None,
        logo: str | ComponentNodeInput | None = None,
        bloks: ActionBloks | None = None,
        dynamic_asks: bool = False,
        dynamic_calls: bool = False,
        dynamic_informs: bool = False,
        estimated_runtime: str | None = None,
        estimated_runtime_ui: str | None = None,
    ) -> WrappedFunction[P, R]:
        """Offer a function as a workflow, as a plain call: ``app.register_workflow(function, name=...)``.

        The twin of :meth:`workflow`, with the same options, for a function that is
        declared somewhere else or offered only under a condition.

        Returns:
            The function, still callable as itself.

        Nothing is built here: a parameter that cannot become a port is reported
        when the app is assembled (:class:`~arkitekt_spec.declare.errors.AppDeclarationError`).
        """
        options = dict(
            name=name,
            description=description,
            actifier=actifier,
            interface=interface,
            stateful=stateful,
            widgets=widgets,
            collections=collections,
            port_groups=port_groups,
            is_test_for=is_test_for,
            validators=validators,
            optimistics=optimistics,
            in_process=in_process,
            locks=locks,
            concurrency=concurrency,
            policy=policy,
            version=version,
            catalogs=catalogs,
            protocols=protocols,
            effects=effects,
            logo=logo,
            execution=Execution.WORKFLOW,
            bloks=bloks,
            dynamic_asks=dynamic_asks,
            dynamic_calls=dynamic_calls,
            dynamic_informs=dynamic_informs,
            estimated_runtime=estimated_runtime,
            estimated_runtime_ui=estimated_runtime_ui,
        )
        return self._offer("register_action", function, options)

    @overload
    def state(
        self,
        cls: C,
        /,
        *,
        name: str | None = None,
        required_locks: list[str] | None = None,
        persist: Literal["synchronous"] | float | None = None,
    ) -> C: ...

    @overload
    def state(
        self,
        /,
        *,
        name: str | None = None,
        required_locks: list[str] | None = None,
        persist: Literal["synchronous"] | float | None = None,
    ) -> Callable[[C], C]: ...

    @dataclass_transform(field_specifiers=(model_field,))
    def state(
        self,
        cls: C | None = None,
        /,
        *,
        name: str | None = None,
        required_locks: list[str] | None = None,
        persist: Literal["synchronous"] | float | None = None,
    ) -> C | Callable[[C], C]:
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
        name: str | None = None,
        required_locks: list[str] | None = None,
        persist: Literal["synchronous"] | float | None = None,
    ) -> C:
        """Declare a class as a state, as a plain call: the twin of :meth:`state`.

        Returns:
            The class.
        """
        if not is_dataclass(cls):
            dataclass(cls)
        self._record(
            "state", cls, name=name, required_locks=required_locks, persist=persist
        )
        return cls

    @overload
    def context(self, cls: C, /) -> C: ...

    @overload
    def context(
        self, /, *, name: str | None = None, locks: list[str] | None = None
    ) -> Callable[[C], C]: ...

    def context(
        self,
        cls: C | None = None,
        /,
        *,
        name: str | None = None,
        locks: list[str] | None = None,
    ) -> C | Callable[[C], C]:
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
        self, cls: C, /, *, name: str | None = None, locks: list[str] | None = None
    ) -> C:
        """Declare a context class, as a plain call: the twin of :meth:`context`.

        Returns:
            The class.
        """
        self._record("context", cls, name=name, locks=locks)
        return cls

    @overload
    def model(
        self,
        cls: C,
        /,
        *,
        identifier: str | None = None,
        description: str | None = None,
    ) -> C: ...

    @overload
    def model(
        self, /, *, identifier: str | None = None, description: str | None = None
    ) -> Callable[[C], C]: ...

    @dataclass_transform(field_specifiers=(model_field,))
    def model(
        self,
        cls: C | None = None,
        /,
        *,
        identifier: str | None = None,
        description: str | None = None,
    ) -> C | Callable[[C], C]:
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

        A malformed identifier (not ``@package/key``) is reported when the app is assembled.
        """

        def declare(cls: C) -> C:
            return self.register_model(
                cls, identifier=identifier, description=description
            )

        if cls is not None:
            return declare(cls)
        return declare

    @dataclass_transform(field_specifiers=(model_field,))
    def register_model(
        self,
        cls: C,
        /,
        *,
        identifier: str | None = None,
        description: str | None = None,
    ) -> C:
        """Declare a model, as a plain call: the twin of :meth:`model`.

        Returns:
            The class, made a dataclass.

        A malformed identifier (not ``@package/key``) is reported when the app is assembled.
        """
        ensure_model_dataclass(cls)
        self._record("model", cls, identifier=identifier, description=description)
        return cls

    def _hook(
        self, kind: str, function: F | None, name: str | None
    ) -> F | Callable[[F], F]:
        def hook(function: F) -> F:
            return self._register_hook(kind, function, name)

        if function is not None:
            return hook(function)
        return hook

    def _register_hook(self, kind: str, function: F, name: str | None) -> F:
        self._record(kind, function, name=name)
        return function

    @overload
    def startup(self, function: F, /) -> F: ...

    @overload
    def startup(self, /, *, name: str | None = None) -> Callable[[F], F]: ...

    def startup(
        self, function: F | None = None, /, *, name: str | None = None
    ) -> F | Callable[[F], F]:
        """Run a function when the app starts providing: ``@app.startup``.

        What it returns sets up the app's states and contexts.

        Args:
            function: The function, when used bare as ``@app.startup``.
            name: The hook's name. Defaults to the function name.

        Returns:
            The function, or, with options, a decorator returning it.
        """
        return self._hook("startup", function, name)

    def register_startup(self, function: F, /, *, name: str | None = None) -> F:
        """Run a function when the app starts providing, as a plain call: the twin of :meth:`startup`.

        Returns:
            The function.
        """
        return self._register_hook("startup", function, name)

    @overload
    def lifecycle(self, function: F, /) -> F: ...

    @overload
    def lifecycle(self, /, *, name: str | None = None) -> Callable[[F], F]: ...

    def lifecycle(
        self, function: F | None = None, /, *, name: str | None = None
    ) -> F | Callable[[F], F]:
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

    def register_lifecycle(self, function: F, /, *, name: str | None = None) -> F:
        """Set up and tear down in one async generator, as a plain call: the twin of :meth:`lifecycle`.

        Returns:
            The function.
        """
        return self._register_hook("lifecycle", function, name)

    @overload
    def shutdown(self, function: F, /) -> F: ...

    @overload
    def shutdown(self, /, *, name: str | None = None) -> Callable[[F], F]: ...

    def shutdown(
        self, function: F | None = None, /, *, name: str | None = None
    ) -> F | Callable[[F], F]:
        """Run a function when the app stops providing: ``@app.shutdown``.

        Args:
            function: The function, when used bare as ``@app.shutdown``.
            name: The hook's name. Defaults to the function name.

        Returns:
            The function, or, with options, a decorator returning it.
        """
        return self._hook("shutdown", function, name)

    def register_shutdown(self, function: F, /, *, name: str | None = None) -> F:
        """Run a function when the app stops providing, as a plain call: the twin of :meth:`shutdown`.

        Returns:
            The function.
        """
        return self._register_hook("shutdown", function, name)

    @overload
    def background(self, function: F, /) -> F: ...

    @overload
    def background(self, /, *, name: str | None = None) -> Callable[[F], F]: ...

    def background(
        self, function: F | None = None, /, *, name: str | None = None
    ) -> F | Callable[[F], F]:
        """Run a function in the background while the app provides: ``@app.background``.

        Args:
            function: The function, when used bare as ``@app.background``.
            name: The task's name. Defaults to the function name.

        Returns:
            The function, or, with options, a decorator returning it.
        """
        return self._hook("background", function, name)

    def register_background(self, function: F, /, *, name: str | None = None) -> F:
        """Run a function in the background while the app provides, as a plain call: the twin of :meth:`background`.

        Returns:
            The function.
        """
        return self._register_hook("background", function, name)

    def blok(
        self,
        name: str,
        component: str | ComponentNodeInput,
        description: str | None = None,
        *,
        demo: BlokDemoInput | Mapping[str, JSONSerializable] | None = None,
        default: bool = False,
        for_model: str | None = None,
        for_node: str | None = None,
        args: Mapping[str, object] | None = None,
        mode: BlokCheckMode = "warning",
    ) -> None:
        r"""Declare a blok of this app's agent (blok language v2):
        ``app.blok("monitor", '<Blok kind="agent" context="panel"><Card/></Blok>')``.

        The blok is one ``<Blok kind="agent" context="panel|scene|logo">`` and declares what
        it owns inside: ``<local name="iterations" default={15} persist />`` (form state a
        control writes through ``bind``, in scope in its parent's subtree; ``like="self.<action>.<arg>"``
        borrows an argument's port), ``<query>`` and ``<subscription>``. ``catalog="..."`` on
        the ``<Blok>`` names the catalog it is written for (the base catalog when left out;
        :data:`arkitekt.ORKESTRATOR_CATALOG_ID` for what only the Orkestrator draws). The tree
        reads the agent as ``self``: ``self.<state>.<field>``, ``self.tasks.<action>``,
        ``self.assets.<name>``, and calls it as ``self.<action>(name: value) into <record>``.
        What it reads of ``self`` becomes its one dependency when the agent is built. It is
        checked now, by the spec's validator, against the language and its catalog: an error
        raises, a warning is a :class:`~arkitekt_spec.declare.catalogs.CatalogWarning`. An
        action's logo (``<Blok kind="action" context="logo"><Logo>...</Logo></Blok>``) is
        declared here too, and named by the action's ``logo=``.

        Args:
            name: The blok's name.
            component: The ``<Blok>``, as v2 BSX or already parsed. A scene holds one
                ``<Scene>``, a logo one ``<Logo>``. A ``<Space>`` belongs to an action
                (``bloks=``).
            description: What the blok shows.
            demo: What a preview renders it with, mirroring the roots it reads:
                ``{"deps": {"self": {...}}, "args": {...}, "queries": {...}}``.
                Placeholders for the states of ``self`` it reads when left out.
            default: Whether this is the app's default blok for its context.
                Declaring another default for the same context replaces it.
            for_model: The model (``"sha256:..."``) this blok decorates: a viewer
                showing that model offers it where ``for_node`` is clicked. Panel
                bloks only.
            for_node: The node of ``for_model`` to attach to; the model's root
                when left out.
            args: The items the blok is opened for, typed like an action's
                arguments (``{"dataset": ArrayDataset}``) and read as
                ``args.dataset``. Panel bloks only.
            mode: ``"warning"`` (the default) warns about a catalog finding,
                ``"strict"`` refuses it.

        Raises:
            ValueError: If the BSX does not parse or the tree breaks a rule of the
                language (a :class:`~arkitekt_spec.blok.vocabulary.BlokError` with its
                code), or the declaration contradicts itself.
        """
        self._record(
            "register_blok",
            name,
            component,
            description=description,
            demo=demo,
            default=default,
            for_model=for_model,
            for_node=for_node,
            args=args,
            mode=mode,
        )

    def register_asset(
        self,
        name: str,
        path: str | Path | None = None,
        kind: AssetKind | None = None,
        *,
        source: str | None = None,
        ref: str | None = None,
    ) -> None:
        """Register a file the app uses, under the name its bloks call it by.

        A blok names it as ``self.assets.<name>``: the model of a scene blok, an
        image in a panel::

            app.register_asset("scope", "models/scope.glb")
            app.register_asset("logo", "art/logo.png")

            app.blok("view", '<Blok kind="agent" context="scene"><Scene><Model src={self.assets.scope} /></Scene></Blok>')
            app.blok("panel", '<Blok kind="agent" context="panel"><Image src={self.assets.logo} /></Blok>')

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
        self._record("register_asset", name, path, kind, source=source, ref=ref)

    def ui_catalog(
        self,
        name: str,
        components: Sequence[ComponentSpec] | None = None,
        operations: Sequence[OperationSpec] | None = None,
        description: str | None = None,
    ) -> None:
        """Declare a module: what a renderer draws and evaluates beyond the spec's catalogs.

        Bloks naming it in their ``<Blok catalog="...">`` are validated against it offline, when they
        are declared, rather than only once the server sees them. The same declaration
        is what a UI app uploads with ``registerModule``.

        Unlike the other declarations this offers nothing and needs no agent: a UI
        app registering its module, or an author declaring one purely to validate,
        should not be made to serve.

        Args:
            name: The module's name, as bloks name it (``<Blok catalog="electron">``).
            components: The components the UI can render.
            operations: Pure operations the UI can evaluate, extending the base catalog.
            description: What the module is.

        Raises:
            ValueError: If it redefines a base operation, or a different module is
                already declared under ``name``.
        """
        self._record(
            "declare_ui_catalog",
            name,
            components=components,
            operations=operations,
            description=description,
        )

    def declare(
        self,
        app: str | None = None,
        *,
        auto_resolvable: bool = False,
        min: int | None = None,
        max: int | None = None,
        version: str | None = None,
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

        A demand naming a class the app cannot make a port of is reported when the
        app is assembled.
        """

        def decorate(cls: C) -> C:
            self._record(
                "declare",
                cls,
                app=app,
                auto_resolvable=auto_resolvable,
                min=min,
                max=max,
                version=version,
            )
            return cls

        return decorate

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
                @ask('<Blok kind="task" context="panel"><Button label="Go" onClick={task.answer(values: {ok: true})} /></Blok>')
                def go(self, name: str) -> Annotated[bool, Key("ok")]:
                    \"\"\"Go on?\"\"\"

                @inform('<Blok kind="task" context="panel"><Text text={args.name} /></Blok>')
                def started(self, name: str) -> None:
                    \"\"\"Started.\"\"\"

            @app.action
            def run(name: str, ui: UI) -> str:
                ui.go(name=name)        # DismissedError when dismissed
                ui.started(name=name)   # shown; the task goes on
                return name

        Returns:
            The class, unchanged.

        A public method that is neither an ask nor an inform, or a blok breaking a rule,
        is reported when the app is assembled.
        """
        self._record("register_interactions", cls)
        return cls

    def register_interactions(self, cls: type[Any], /) -> None:
        """Declare an interactions protocol, as a plain call: the twin of :meth:`interactions`."""
        self._record("register_interactions", cls)

    def register_protocol(
        self,
        cls: C,
        /,
        app: str | None = None,
        *,
        auto_resolvable: bool = False,
        min: int | None = None,
        max: int | None = None,
        version: str | None = None,
    ) -> C:
        """Declare a protocol, as a plain call: the twin of :meth:`declare`.

        Returns:
            The class, unchanged.

        A demand naming a class the app cannot make a port of is reported when the
        app is assembled.
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
        shrink: Callable[..., Any] | None = None,
        description: str | None = None,
        default_widget: AssignWidgetInput | None = None,
        describe: Callable[[Any], Mapping[str, Any]] | None = None,
    ) -> None:
        """Declare a type that travels by id, with your own way of fetching it back.

        For a type a *shared library* defines -- one that both the sending and the
        receiving app know, because both import it, and no ``@structure`` marks. A
        client package's own types are marked with ``@structure`` instead.

        The expander says what it needs by annotation, the same way an action
        does, and a run hands it exactly those::

            async def expand_thing(id: str, mikro: Mikro) -> Thing:
                return Thing(await mikro.aget_file(id))

            app.register_structure(Thing, "@lib/thing", expand=expand_thing)

        It must be a named function with annotated parameters: a lambda has no
        annotations, so there would be nothing to read.

        The clients its expander asks for are used by the app, like an action's.

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

        A malformed identifier, or an expander whose parameters cannot be read or are
        not clients, is reported when the app is assembled.
        """
        self._record(
            "register_as_structure",
            cls,
            identifier=identifier,
            aexpand=expand,
            ashrink=shrink or id_shrink,
            description=description,
            default_widget=default_widget,
            describe=describe,
        )

    def memory_structure(
        self, cls: type, identifier: str | None = None, description: str | None = None
    ) -> None:
        """Declare a class whose instances stay on the agent: ``app.memory_structure(np.ndarray)``.

        Nothing is registered automatically: a port names a class some client's
        ``@structure`` declares, or one declared here.

        Args:
            cls: The class to keep on the agent.
            identifier: What it travels as. Defaults to the class name in the app's
                namespace for a class the app defines (``@myapp/blob``), else in its
                module (``numpy.ndarray`` -> ``@numpy/ndarray``).
            description: What it is, for the UI.
        """
        self._record(
            "register_memory_structure",
            cls,
            identifier=identifier,
            description=description,
        )
