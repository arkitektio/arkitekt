"""arkitekt: declare an app, run it, and then let your friends run it too.

    from arkitekt import App, Task, run

    app = App("my-app", app_context=Config)

    @app.action
    def measure(x: int, task: Task) -> int:
        ... your code here ...

    run(app, context=Config())

Most exports are usable through ``from arkitekt import ...`` so just import what you need.

Depending on your use case, you may need to install extra dependencies. arkitekt is split into three main parts:
- arkitekt-spec: the declarations and their types, which are used to declare an app and its actions, and to inspect and validate them. This is the only part that is needed to declare an app. It
however does not run an app, and does not connect to services.
- arkitekt-runtime: the runtime that runs an app, connects it to services, and manages its lifecycle. This is needed if you have declared
actions and states and want to run them, or if you want to connect to services. It does however not a transport to give a task to your app.
- arkitekt-fastapi: a transport that serves an app over HTTP, so that other apps can call it.
- rekuest: a transport that runs an app in distributed mode, so that other apps can call it. This is needed if you want to run your app in distributed mode, but not if you just want to run it or connect to services.

"""

from arkitekt_spec.actions import (
    ActionDemandInput,
    ActionDependencyInput,
    AgentDependencyInput,
    ArgPortInput,
    ReturnPortInput,
    AssetKind,
    BlokDemoInput,
    BlokLocalInput,
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
from arkitekt_spec.declare.actors.policy import (
    CancelOnDisconnect,
    DisconnectPolicy,
    OnDisconnect,
)
from arkitekt_spec.declare.actors.types import Actifier
from arkitekt_spec.declare.agents.connection import (
    ConnectionListener,
    ConnectionState,
    TaskEvent,
    TaskEventKind,
    TaskListener,
)
from arkitekt_spec.declare.agents.errors import NoCallerError
from arkitekt_spec.declare.annotations import (
    Default,
    Description,
    Key,
    Provides,
    Fits,
    Requires,
    Units,
)
from arkitekt_spec.declare.app import AppRegistry
from arkitekt_spec.declare.interactions import AskMethod, InformMethod, ask, inform
from arkitekt_spec.declare.blok.from_svg import (
    SvgConversionError,
    SvgConversionWarning,
    from_svg,
)
from arkitekt_spec.declare.blok.action import ActionBlok
from arkitekt_spec.declare.blok.parser import bsx, parse_util_call
from arkitekt_spec.declare.blok.declarations import Local, Query, Subscription
from arkitekt_spec.declare.blok.unparse import to_bsx
from arkitekt_spec.declare.blok.validate import (
    BlokScope,
    check_blok_tree,
    validate_blok,
    validate_bsx,
)
from arkitekt_spec.blok.bsx import parse_bsx, parse_bsx_with_spans
from arkitekt_spec.blok.prompt import (
    blok_prompt,
    component_signature,
    function_signature,
)
from arkitekt_spec.blok.catalogs import (
    ORKESTRATOR_MODULE,
    STANDARD_CATALOGS,
    BlokView,
    blok_view,
    default_view,
    orkestrator_module,
    standard_catalog,
)
from arkitekt_spec.declare.blok.registry import catalogs_of
from arkitekt_spec.blok.vocabulary import BlokError, Finding, Function, load_vocabulary
from arkitekt_spec.declare.catalogs import (
    BLOK_ARGS_ROOT,
    BlokCheckMode,
    Catalog,
    CatalogView,
    ComponentSpec,
    Diagnostic,
    OperationSpec,
    standard_view,
    parse_ui_catalog,
    ui_catalog_view,
)
from arkitekt_spec.declare.coercible_types import ToOptimisticProtocol
from arkitekt_spec.declare.errors import (
    AgentLost,
    DeniedError,
    DismissedError,
    NonDeterministicWorkflow,
    NotAWorkflowError,
    NotDeclaredError,
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
    TaskBlok,
    aretry,
    retry,
)
from arkitekt_spec.declare.widgets import withEffect, withValidator
from fakts.grants.remote.authorizers.device_code import DeviceCodeChallenge
from fakts.mesh import MeshOptions, MeshProxy

from .app.app import App, merge
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
    "merge",
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
    "TaskBlok",
    # the bloks an action asks through or shows, declared (`@app.interactions`)
    "ask",
    "inform",
    "AskMethod",
    "InformMethod",
    "DismissedError",
    "NotDeclaredError",
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
    # bloks, catalogs and modules
    "AgentDependencyInput",
    "ActionDependencyInput",
    "StateDependencyInput",
    "ActionDemandInput",
    "StateDemandInput",
    "PortMatchInput",
    "ArgPortInput",
    "ReturnPortInput",
    "ComponentNodeInput",
    "ComponentPropInput",
    "validate_blok",
    "validate_bsx",
    "BlokScope",
    "check_blok_tree",
    "parse_bsx",
    "parse_bsx_with_spans",
    "BlokView",
    "BlokDemoInput",
    "BlokLocalInput",
    "parse_ui_catalog",
    "blok_view",
    "default_view",
    "STANDARD_CATALOGS",
    "ORKESTRATOR_MODULE",
    "standard_catalog",
    "orkestrator_module",
    "catalogs_of",
    "BlokError",
    "Finding",
    "load_vocabulary",
    "Function",
    "Local",
    "Query",
    "Subscription",
    "BLOK_ARGS_ROOT",
    "standard_view",
    "ui_catalog_view",
    "Diagnostic",
    "BlokCheckMode",
    "Catalog",
    "CatalogView",
    "ComponentSpec",
    "OperationSpec",
    "model_field",
    "ActionBlok",
    "bsx",
    "to_bsx",
    "blok_prompt",
    "component_signature",
    "function_signature",
    "from_svg",
    "ComponentContext",
    "SvgConversionError",
    "SvgConversionWarning",
    "parse_util_call",
    "withValidator",
    "withEffect",
    "Description",
    "Key",
    "Fits",
    "Requires",
    "Provides",
    "DescriptorOperator",
    "Units",
    "Default",
    "DisconnectPolicy",
    "CancelOnDisconnect",
    "OnDisconnect",
]
