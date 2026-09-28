"""arkitekt: declare an app, run it, call others. The one import an app author needs.

    from arkitekt import App, Task, run

    app = App("my-app", app_context=Config)

    @app.action
    def measure(x: int, task: Task) -> int: ...

    run(app, context=Config())

An app is declared with arkitekt-spec (:mod:`arkitekt_spec.declare`); what goes
*inside* a declaration is re-exported here, so an app imports ``arkitekt`` alone:
``Task``, ``model_field``, ``bsx``, ``withValidator``/``withEffect``, the
``Annotated`` markers, the disconnect policies, and the widgets in
:mod:`arkitekt.widgets`.

arkitekt does not depend on a runtime. ``run(app)`` runs the app in distributed mode
through rekuest and ``serve(app, fastapi_app)`` serves it over HTTP (arkitekt-fastapi):
install ``arkitekt[rekuest]`` / ``arkitekt[serve]`` for those. Declaring,
inspecting and building an app, and ``connect(app)`` to services, need neither.
"""

from arkitekt_spec.declare.actors.policy import CancelOnDisconnect, DisconnectPolicy, OnDisconnect
from arkitekt_spec.declare.annotations import Default, Description, Provides, Requires, Units
from arkitekt_spec.declare.app import AppRegistry
from arkitekt_spec.declare.blok.parser import bsx, parse_util_call
from arkitekt_spec.declare.structures.model import model_field
from arkitekt_spec.declare.task import Task
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
    "Task",
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
