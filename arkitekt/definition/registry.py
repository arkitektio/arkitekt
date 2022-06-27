import contextvars
from arkitekt.api.schema import DefinitionInput
from arkitekt.actors.actify import actify
from arkitekt.definition.define import prepare_definition
from arkitekt.structures.registry import (
    StructureRegistry,
    get_current_structure_registry,
)
from arkitekt.api.schema import WidgetInput
from typing import Dict, List, Callable, Optional, Tuple
from pydantic import Field
from koil.composition import KoiledModel


current_definition_registry = contextvars.ContextVar(
    "current_definition_registry", default=None
)
GLOBAL_DEFINITION_REGISTRY = None


def get_default_definition_registry():
    global GLOBAL_DEFINITION_REGISTRY
    if GLOBAL_DEFINITION_REGISTRY is None:
        GLOBAL_DEFINITION_REGISTRY = DefinitionRegistry()
    return GLOBAL_DEFINITION_REGISTRY


def get_current_definition_registry(allow_global=True):
    return current_definition_registry.get(get_default_definition_registry())


QString = str


class DefinitionRegistry(KoiledModel):
    structure_registry: Optional[StructureRegistry] = None
    defined_nodes: List[Tuple[DefinitionInput, Callable]] = Field(
        default_factory=list, exclude=True
    )
    templated_nodes: List[Tuple[QString, Callable]] = Field(
        default_factory=list, exclude=True
    )
    copy_from_default: bool = False

    _token: contextvars.Token = None

    def __post_init__(self):
        if self.copy_from_default:
            default = get_default_definition_registry()
            self.defined_nodes = default.defined_nodes + self.defined_nodes
            self.templated_nodes = default.templated_nodes + self.templated_nodes

    def has_definitions(self):
        return len(self.definedNodes) > 0 or len(self.templatedNodes) > 0

    def reset(self):
        self.definedNodes = []  # dict are queryparams for the node
        self.templatedNodes = []

    def register_actor_with_defintion(
        self, actorBuilder: Callable, definition: DefinitionInput, **params  # New Node
    ):
        self.defined_nodes.append((definition, actorBuilder, params))

    def register_actor_with_template(
        self, actorBuilder: Callable, q_string: QString, **params
    ):  # Query Path
        self.templated_nodes.append((q_string, actorBuilder, params))

    def register(
        self,
        function,
        builder=None,
        package=None,
        interface=None,
        widgets: Dict[str, WidgetInput] = {},
        interfaces: List[str] = [],
        on_provide=None,
        on_unprovide=None,
        structure_registry: StructureRegistry = None,
        **actorparams,
    ):

        structure_registry = (
            structure_registry
            or self.structure_registry
            or get_current_structure_registry()
        )

        actorBuilder = actify(
            function,
            builder=builder,
            on_provide=on_provide,
            on_unprovide=on_unprovide,
            structure_registry=structure_registry,
            **actorparams,
        )

        definition = prepare_definition(
            function=function,
            widgets=widgets,
            package=package,
            interface=interface,
            interfaces=interfaces,
            structure_registry=structure_registry,
        )

        self.register_actor_with_defintion(actorBuilder, definition, **actorparams)

    def template(
        self,
        function,
        qstring: QString,
        on_provide=None,
        on_unprovide=None,
        structure_registry: StructureRegistry = None,
        **actorparams,
    ):
        structure_registry = (
            structure_registry
            or self.structure_registry
            or get_current_structure_registry()
        )

        actorBuilder = actify(
            function,
            on_provide=on_provide,
            on_unprovide=on_unprovide,
            structure_registry=structure_registry ** actorparams,
        )

        self.register_actor_with_template(actorBuilder, qstring, **actorparams)

    async def __aenter__(self):
        self.structure_registry = (
            self.structure_registry or get_current_structure_registry()
        )
        current_definition_registry.set(self)
        return self

    async def __exit__(self, *args, **kwargs):
        current_definition_registry.set(None)


def register(
    widgets: Dict[str, WidgetInput] = {},
    interfaces: List[str] = [],
    on_provide=None,
    on_unprovide=None,
    definition_registry: DefinitionRegistry = None,
    structure_registry: StructureRegistry = None,
    **params,
):
    """Take a function and register it as a node.

    This function is used to register a node. Use it as a decorator. You can specify
    specific widgets for every paramer in a dictionary {argument_key: widget}. By default
    this function will use the default defintion registry to store the nodes inputdata.
    This definition registry will then be used by an agent to create, and provide the node.

    If your function has specific inputs that need custom rules for expansion and shrinking
     , you can pass a structure registry to the function. This registry will then be used.

    This decorator is non intrusive. You can still call this function as a normal function from
    your code

    Args:
        widgets (Dict[str, WidgetInput], optional): _description_. Defaults to {}.
        interfaces (List[str], optional): _description_. Defaults to [].
        on_provide (_type_, optional): _description_. Defaults to None.
        on_unprovide (_type_, optional): _description_. Defaults to None.
        definition_registry (DefinitionRegistry, optional): _description_. Defaults to None.
        structure_registry (StructureRegistry, optional): _description_. Defaults to None.

    Returns:
        Callable: A wrapped function that just returns the original function.
    """
    definition_registry = definition_registry or get_current_definition_registry()
    structure_registry = structure_registry or get_current_structure_registry()

    def real_decorator(function):
        # Simple bypass for now
        def wrapped_function(*args, **kwargs):
            return function(*args, **kwargs)

        definition_registry.register(
            function,
            widgets=widgets,
            interfaces=interfaces,
            structure_registry=structure_registry,
            on_provide=on_provide,
            on_unprovide=on_unprovide,
            **params,
        )

    return real_decorator


def template(
    q_string: QString,
    on_provide=None,
    on_unprovide=None,
    structure_registry: StructureRegistry = None,
    definition_registry: DefinitionRegistry = None,
    **params,
):

    definition_registry = definition_registry or get_current_definition_registry()
    structure_registry = structure_registry or get_current_structure_registry()

    def real_decorator(function):
        # Simple bypass for now
        def wrapped_function(*args, **kwargs):
            return function(*args, **kwargs)

        definition_registry.template(
            function,
            q_string,
            on_provide=on_provide,
            on_unprovide=on_unprovide,
            structure_registry=structure_registry,
            **params,
        )

        # We are registering this as a template

        return wrapped_function

    return real_decorator
