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
    ActionDemandInput,
    ActionDependencyInput,
    AgentDependencyInput,
    AssetKind,
    ComponentContext,
    ComponentNodeInput,
    ComponentPropInput,
    DescriptorOperator,
    EffectInput,
    Effects,
    Execution,
    OptimisticInput,
    PortGroupInput,
    PortKind,
    PortMatchInput,
    StateDemandInput,
    StateDependencyInput,
    TestTargetInput,
    TrackInput,
    UtilCallInput,
    ValidatorInput,
)
from arkitekt_spec.declare.actors.policy import CancelOnDisconnect, DisconnectPolicy, OnDisconnect
from arkitekt_spec.declare.actors.types import Actifier
from arkitekt_spec.declare.agents.connection import (
    ConnectionListener,
    ConnectionState,
    TaskEvent,
    TaskEventKind,
    TaskListener,
)
from arkitekt_spec.declare.agents.errors import NoCallerError
from arkitekt_spec.declare.annotations import Default, Description, Provides, Requires, Units
from arkitekt_spec.declare.app import AppRegistry
from arkitekt_spec.declare.blok.from_svg import SvgConversionError, SvgConversionWarning, from_svg
from arkitekt_spec.declare.blok.parser import bsx, parse_util_call
from arkitekt_spec.declare.blok.registry import demo_state_for
from arkitekt_spec.declare.blok.unparse import to_bsx
from arkitekt_spec.declare.blok.validate import (
    RESERVED_ROOTS,
    check_context_root,
    check_logo_complexity,
    check_logo_palette,
    local_roots_of,
    validate_blok,
)
from arkitekt_spec.declare.catalogs import (
    CatalogView,
    ComponentSpec,
    Diagnostic,
    OperationSpec,
    standard_view,
)
from arkitekt_spec.declare.coercible_types import ToOptimisticProtocol
from arkitekt_spec.declare.errors import (
    AgentLost,
    DeniedError,
    NonDeterministicWorkflow,
    NotAWorkflowError,
    StateChanged,
    StatePreconditionFailed,
)
from arkitekt_spec.declare.provider import Provider
from arkitekt_spec.declare.register import WrappedFunction
from arkitekt_spec.declare.service import Service
from arkitekt_spec.declare.structures.model import model_field
from arkitekt_spec.declare.targets import CallTarget, ImplementationTarget
from arkitekt_spec.declare.task import (
    AssignmentHook,
    AssignPrompt,
    Decision,
    HookInput,
    HookKind,
    LogLevel,
    StateRef,
    StateRequirement,
    Task,
    aretry,
    retry,
)
from arkitekt_spec.declare.widgets import withEffect, withValidator
from fakts.grants.remote.authorizers.device_code import DeviceCodeChallenge
from fakts.mesh import MeshOptions, MeshProxy

from .app.app import App
from .app.sources import DISCOVER, Source
from .inspect import inspect
from .runtime import (
    DetachedRun,
    Runtime,
    arun,
    connect,
    has_stored_login,
    logout,
    run,
    run_detached,
)
from .serve import serve
from .shortcuts import Easy, aeasy, easy, interactive

__all__ = [
    # the app and its runs
    "App",
    "Source",
    "DISCOVER",
    "Runtime",
    "arun",
    "connect",
    "run",
    "serve",
    # beside a program with a life of its own
    "run_detached",
    "DetachedRun",
    "ConnectionState",
    "ConnectionListener",
    "TaskEvent",
    "TaskEventKind",
    "TaskListener",
    "DeviceCodeChallenge",
    "has_stored_login",
    "logout",
    "Easy",
    "easy",
    "aeasy",
    "interactive",
    "inspect",
    # how a run reaches services on the deployment's mesh
    "MeshOptions",
    "MeshProxy",
    # what goes inside a declaration
    "AppRegistry",
    "AssetKind",
    "Service",
    "Provider",
    "WrappedFunction",
    "Actifier",
    # the task an action runs as
    "Task",
    "LogLevel",
    "AssignmentHook",
    "AssignPrompt",
    "Decision",
    "HookInput",
    "HookKind",
    "CallTarget",
    "ImplementationTarget",
    "NoCallerError",
    # what a workflow uses when a step is lost or the world moved
    "AgentLost",
    "DeniedError",
    "NonDeterministicWorkflow",
    "NotAWorkflowError",
    "StateChanged",
    "StateRef",
    # what a call says the agent's state must hold
    "StateRequirement",
    "StatePreconditionFailed",
    "aretry",
    "retry",
    # what @app.action takes
    "PortGroupInput",
    "EffectInput",
    "Effects",
    "Execution",
    "ValidatorInput",
    "UtilCallInput",
    "TrackInput",
    "TestTargetInput",
    "OptimisticInput",
    "ToOptimisticProtocol",
    "PortKind",
    # bloks and UI catalogs
    "AgentDependencyInput",
    "ActionDependencyInput",
    "StateDependencyInput",
    "ActionDemandInput",
    "StateDemandInput",
    "PortMatchInput",
    "ComponentNodeInput",
    "ComponentPropInput",
    "validate_blok",
    "check_context_root",
    "check_logo_complexity",
    "check_logo_palette",
    "RESERVED_ROOTS",
    "local_roots_of",
    "demo_state_for",
    "standard_view",
    "Diagnostic",
    "CatalogView",
    "ComponentSpec",
    "OperationSpec",
    "model_field",
    "bsx",
    "to_bsx",
    "from_svg",
    "ComponentContext",
    "SvgConversionError",
    "SvgConversionWarning",
    "parse_util_call",
    "withValidator",
    "withEffect",
    "Description",
    "Requires",
    "Provides",
    "DescriptorOperator",
    "Units",
    "Default",
    "DisconnectPolicy",
    "CancelOnDisconnect",
    "OnDisconnect",
]
