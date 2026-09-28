"""arkitekt: declare an app, run it, call others. The one import an app author needs.

    from arkitekt import App, Task, run

    app = App("my-app", app_context=Config)

    @app.action
    def measure(x: int, task: Task) -> int: ...

    run(app, context=Config())

``from arkitekt import ...`` is the canonical import for an app. Everything an app
writes is here: the task it runs as (``Task``, what it logs and calls, and the
errors a call can raise), the ``Annotated`` markers, the options ``@app.action``
takes, the blok and catalog models, and the widgets in :mod:`arkitekt.widgets`.
They are defined in arkitekt-spec, which is the definition space the SDKs and
runtimes build on; an app should not need to import it.

arkitekt does not depend on a runtime. ``run(app)`` runs the app in distributed mode
through rekuest and ``serve(app, fastapi_app)`` serves it over HTTP (arkitekt-fastapi):
install ``arkitekt[rekuest]`` / ``arkitekt[serve]`` for those. Declaring,
inspecting and building an app, and ``connect(app)`` to services, need neither.
"""

from arkitekt_spec.actions import (
    AgentDependencyInput,
    ComponentNodeInput,
    ComponentPropInput,
    EffectInput,
    OptimisticInput,
    PortGroupInput,
    PortKind,
    TestTargetInput,
    TrackInput,
    UtilCallInput,
    ValidatorInput,
)
from arkitekt_spec.declare.actors.policy import CancelOnDisconnect, DisconnectPolicy, OnDisconnect
from arkitekt_spec.declare.actors.types import Actifier
from arkitekt_spec.declare.agents.errors import NoCallerError
from arkitekt_spec.declare.annotations import Default, Description, Provides, Requires, Units
from arkitekt_spec.declare.app import AppRegistry
from arkitekt_spec.declare.blok.parser import bsx, parse_util_call
from arkitekt_spec.declare.blok.validate import validate_blok
from arkitekt_spec.declare.catalogs import CatalogView, ComponentSpec, Diagnostic, OperationSpec
from arkitekt_spec.declare.coercible_types import ToOptimisticProtocol
from arkitekt_spec.declare.provider import Provider
from arkitekt_spec.declare.register import WrappedFunction
from arkitekt_spec.declare.service import Service
from arkitekt_spec.declare.structures.model import model_field
from arkitekt_spec.declare.targets import CallTarget, ImplementationTarget
from arkitekt_spec.declare.task import AssignmentHook, LogLevel, Task
from arkitekt_spec.declare.widgets import withEffect, withValidator

from .app.app import App
from .inspect import inspect
from .runtime import Runtime, arun, connect, run
from .serve import serve
from .shortcuts import Easy, aeasy, easy, interactive

__all__ = [
    # the app and its runs
    "App",
    "Runtime",
    "arun",
    "connect",
    "run",
    "serve",
    "Easy",
    "easy",
    "aeasy",
    "interactive",
    "inspect",
    # what goes inside a declaration
    "AppRegistry",
    "Service",
    "Provider",
    "WrappedFunction",
    "Actifier",
    # the task an action runs as
    "Task",
    "LogLevel",
    "AssignmentHook",
    "CallTarget",
    "ImplementationTarget",
    "NoCallerError",
    # what @app.action takes
    "PortGroupInput",
    "EffectInput",
    "ValidatorInput",
    "UtilCallInput",
    "TrackInput",
    "TestTargetInput",
    "OptimisticInput",
    "ToOptimisticProtocol",
    "PortKind",
    # bloks and UI catalogs
    "AgentDependencyInput",
    "ComponentNodeInput",
    "ComponentPropInput",
    "validate_blok",
    "Diagnostic",
    "CatalogView",
    "ComponentSpec",
    "OperationSpec",
    "model_field",
    "bsx",
    "parse_util_call",
    "withValidator",
    "withEffect",
    "Description",
    "Requires",
    "Provides",
    "Units",
    "Default",
    "DisconnectPolicy",
    "CancelOnDisconnect",
    "OnDisconnect",
]
