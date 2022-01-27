from arkitekt.api.schema import DefinitionInput, NodeFragment
from arkitekt.actors.actify import actify
from arkitekt.definition.define import prepare_definition
from arkitekt.structures.registry import (
    StructureRegistry,
    get_current_structure_registry,
)
from arkitekt.api.schema import WidgetInput
from .base import Actor
from typing import Dict, List, Callable, Tuple


class ActorRegistry:
    def __init__(self) -> None:
        self.templatedUnqueriedNodes: List[
            Tuple[dict, Callable]
        ] = []  # dict are queryparams for the node
        self.templatedNodes: List[
            Tuple[NodeFragment, Callable]
        ] = []  # node is already saved and has id
        self.templatedNewNodes: List[Tuple[NodeFragment, Callable]] = []
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
            Tuple[NodeFragment, Callable]
        ] = []  # node is already saved and has id
        self.templatedNewNodes: List[Tuple[NodeFragment, Callable]] = []

    def register(
        self,
        actorBuilder: Callable[..., Actor],
        definition: DefinitionInput = None,  # New Node
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
    widgets: Dict[str, WidgetInput] = {},
    interfaces: List[str] = [],
    on_provide=None,
    on_unprovide=None,
    actor_registry: ActorRegistry = None,
    structure_registry: StructureRegistry = None,
    **params
):
    registry = actor_registry or get_current_actor_registry()
    structure_registry = structure_registry or get_current_structure_registry()

    def real_decorator(function):
        # Simple bypass for now
        def wrapped_function(*args, **kwargs):
            return function(*args, **kwargs)

        actorBuilder = actify(
            function,
            on_provide=on_provide,
            on_unprovide=on_unprovide,
            structure_registry=structure_registry,
            **params,
        )

        definition = prepare_definition(
            function=function,
            widgets=widgets,
            interfaces=interfaces,
            structure_registry=structure_registry,
        )
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
