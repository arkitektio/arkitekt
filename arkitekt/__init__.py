"""arkitekt: declare an app, run it, call others. The one import an app author needs.

    from arkitekt import App, Task, run

    app = App("my-app", app_context=Config)

    @app.action
    def measure(x: int, task: Task) -> int: ...

    run(app, context=Config())

What goes *inside* a declaration is re-exported from rekuest here, so an app
never imports rekuest itself: ``Task``, ``model_field``, ``bsx``,
``withValidator``/``withEffect``, the ``Annotated`` markers, the policies, and
the widgets in :mod:`arkitekt.widgets`. The ``Rekuest`` client and the
generated schema types stay rekuest's: a service, taken by annotation.
"""

from rekuest.actors.policy import CancelOnDisconnect, DisconnectPolicy, OnDisconnect
from rekuest.agents.policy import Backoff, ConnectionPolicy
from rekuest.annotations import Default, Description, Provides, Requires, Units
from rekuest.app import AppRegistry
from rekuest.blok.parser import bsx, parse_util_call
from rekuest.structures.model import model_field
from rekuest.task import Task
from rekuest.widgets import withEffect, withValidator

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
    "ConnectionPolicy",
    "Backoff",
]
