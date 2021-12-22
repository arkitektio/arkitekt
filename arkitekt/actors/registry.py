from arkitekt.actors.actify import actify, define
from arkitekt.schema.widgets import Widget
from .base import Actor
from arkitekt.schema import Node
from typing import Dict, List, Callable, Tuple


class ActorRegistry:
    def __init__(self) -> None:
        self.templatedUnqueriedNodes: List[
            Tuple[dict, Callable]
        ] = []  # dict are queryparams for the node
        self.templatedNodes: List[
            Tuple[Node, Callable]
        ] = []  # node is already saved and has id
        self.templatedNewNodes: List[Tuple[Node, Callable]] = []
        # Node is not saved and has undefined id

    def has_actors(self):
        return (
            len(self.templatedNewNodes) > 0
            or len(self.templatedNodes) > 0
            or len(self.templatedUnqueriedNodes) > 0
        )

    def reset(self):
        self.templatedUnqueriedNodes: List[
            Tuple[dict, Callable]
        ] = []  # dict are queryparams for the node
        self.templatedNodes: List[
            Tuple[Node, Callable]
        ] = []  # node is already saved and has id
        self.templatedNewNodes: List[Tuple[Node, Callable]] = []

    def register(
        self,
        actorBuilder: Callable[..., Actor],
        definition: Node = None,  # New Node
        q_string: str = None,  # Query an already existing Node
        **params
    ):

        if definition:
            self.templatedNewNodes.append((definition, actorBuilder, params))

        if q_string:
            self.templatedUnqueriedNodes.append(({"q": q_string}, actorBuilder, params))

        pass


ACTOR_REGISTRY = None


def get_current_actor_registry():
    global ACTOR_REGISTRY
    if not ACTOR_REGISTRY:
        ACTOR_REGISTRY = ActorRegistry()
    return ACTOR_REGISTRY


def register(
    widgets: Dict[str, Widget] = {},
    interfaces: List[str] = [],
    on_provide=None,
    on_unprovide=None,
    registry: ActorRegistry = None,
    **params
):
    registry = get_current_actor_registry()

    def real_decorator(function):
        # Simple bypass for now
        def wrapped_function(*args, **kwargs):
            return function(*args, **kwargs)

        actorBuilder = actify(
            function, on_provide=on_provide, on_unprovide=on_unprovide, **params
        )

        definition = define(function=function, widgets=widgets, interfaces=interfaces)
        registry.register(actorBuilder, definition=definition, **params)

        return wrapped_function

    return real_decorator


def template(q_string, on_provide=None, on_unprovide=None, **params):

    registry = get_current_actor_registry()

    def real_decorator(function):
        # Simple bypass for now
        def wrapped_function(*args, **kwargs):
            return function(*args, **kwargs)

        actorBuilder = actify(
            function, on_provide=on_provide, on_unprovide=on_unprovide, **params
        )

        registry.register(actorBuilder, q_string=q_string, **params)

        # We are registering this as a template

        return wrapped_function

    return real_decorator
