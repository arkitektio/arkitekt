from typing import Dict, List
from arkitekt.actors.actify import actify, define

from arkitekt.actors.registry import ActorRegistry, get_current_actor_registry
from arkitekt.qt.actor import QtActor
from arkitekt.schema.widgets import Widget


def register_ui(
    widgets: Dict[str, Widget] = {},
    interfaces: List[str] = [],
    on_provide=None,
    on_unprovide=None,
    registry: ActorRegistry = None,
    timeout: int = 5000,
    **params
):
    registry = get_current_actor_registry()

    def real_decorator(function):
        # Simple bypass for now
        def wrapped_function(*args, **kwargs):
            return function(*args, **kwargs)

        defined_actor = QtActor(
            qt_assign=function,
            qt_on_provide=on_provide,
            qt_on_unprovide=on_unprovide,
            timeout=timeout,
            **params
        )

        actor_builder = lambda: defined_actor

        definition = define(function=function, widgets=widgets, interfaces=interfaces)
        registry.register(actor_builder, definition=definition, **params)

        return wrapped_function

    return real_decorator
