import contextvars
from arkitekt.api.schema import DefinitionInput, NodeFragment
from arkitekt.actors.actify import actify
from arkitekt.definition.define import prepare_definition
from arkitekt.definition.errors import NoDefinitionRegistryFound
from arkitekt.structures.registry import (
    StructureRegistry,
    get_current_structure_registry,
)
from arkitekt.api.schema import WidgetInput
from typing import Dict, List, Callable, Tuple
import os


current_definition_registry = contextvars.ContextVar(
    "current_definition_registry", default=None
)
GLOBAL_DEFINITION_REGISTRY = None


def set_current_definition_registry(herre, set_global=True):
    global GLOBAL_DEFINITION_REGISTRY
    current_definition_registry.set(herre)
    if set_global:
        GLOBAL_DEFINITION_REGISTRY = herre


def set_global_definition_registry(herre):
    global GLOBAL_DEFINITION_REGISTRY
    GLOBAL_DEFINITION_REGISTRY = herre


def get_current_definition_registry(allow_global=True):
    global GLOBAL_DEFINITION_REGISTRY
    arkitekt = current_definition_registry.get()

    if not arkitekt:
        if not allow_global:
            raise NoDefinitionRegistryFound(
                "No current_definition_registry found and global mikro are not allowed"
            )
        if not GLOBAL_DEFINITION_REGISTRY:
            if os.getenv("ARKITEKT_ALLOW_DEFINITION_REGISTRY_GLOBAL", "True") == "True":
                try:
                    GLOBAL_DEFINITION_REGISTRY = DefinitionRegistry()
                    return GLOBAL_DEFINITION_REGISTRY
                except ImportError as e:
                    raise NoDefinitionRegistryFound("Error creating Fakts Mikro") from e
            else:
                raise NoDefinitionRegistryFound(
                    "No current mikro found and and no global mikro found"
                )

        return GLOBAL_DEFINITION_REGISTRY

    return arkitekt


QString = str


class DefinitionRegistry:
    def __init__(self) -> None:
        self.definedNodes: List[
            Tuple[DefinitionInput, Callable]
        ] = []  # node is already saved and has id
        self.templatedNodes: List[Tuple[QString, Callable]] = []
        # Node is not saved and has undefined id

    def has_actors(self):
        return len(self.definedNodes) > 0 or len(self.templatedNodes) > 0

    def reset(self):
        self.definedNodes = []  # dict are queryparams for the node
        self.templatedNodes = []

    def register(
        self, actorBuilder: Callable, definition: DefinitionInput, **params  # New Node
    ):
        self.definedNodes.append((definition, actorBuilder, params))
        pass

    def template(
        self, actorBuilder: Callable, q_string: QString, **params
    ):  # Query Path
        self.templatedNodes.append((q_string, actorBuilder, params))
        pass


def register(
    widgets: Dict[str, WidgetInput] = {},
    interfaces: List[str] = [],
    on_provide=None,
    on_unprovide=None,
    definition_registry: DefinitionRegistry = None,
    structure_registry: StructureRegistry = None,
    **params
):
    registry = definition_registry or get_current_definition_registry()
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
        registry.register(actorBuilder, definition, **params)

        return wrapped_function

    return real_decorator


def template(q_string: QString, on_provide=None, on_unprovide=None, **params):

    registry = get_current_definition_registry()

    def real_decorator(function):
        # Simple bypass for now
        def wrapped_function(*args, **kwargs):
            return function(*args, **kwargs)

        actorBuilder = actify(
            function, on_provide=on_provide, on_unprovide=on_unprovide, **params
        )

        registry.register(actorBuilder, q_string, **params)

        # We are registering this as a template

        return wrapped_function

    return real_decorator
