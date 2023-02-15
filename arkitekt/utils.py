from typing import Awaitable, Callable, Dict, List, Union
from rekuest.api.schema import ProvisionFragment, WidgetInput
from rekuest.definition.registry import ActorBuilder, get_default_definition_registry
from rekuest.structures.registry import StructureRegistry
from rekuest.structures.default import get_default_structure_registry
from rekuest.actors.base import Actor
from rekuest.actors.actify import Actifier
import os

def register(
    actifier: Actifier = None,
    interface: str = None,
    widgets: Dict[str, WidgetInput] = None,
    interfaces: List[str] = [],
    on_provide=None,
    on_unprovide=None,
    structure_registry: StructureRegistry = None,
    **actifier_params,
):
    """Register a function or actor to the default definition registry.

    This is a convenience function to register a function or actor to the default definition registry.
    It is equivalent to calling the register method on the default definition registry.

    Args:
        function_or_actor (Union[Callable, Actor]): The function or Actor
        builder (ActorBuilder, optional): An actor builder (see ActorBuilder). Defaults to None.
        package (str, optional): The package you want to register this function in. Defaults to standard app package    .
        interface (str, optional): The name of the function. Defaults to the functions name.
        widgets (Dict[str, WidgetInput], optional): A dictionary of parameter key and a widget. Defaults to the default widgets as registered in the structure registry .
        interfaces (List[str], optional): Interfaces that this node adheres to. Defaults to [].
        on_provide (Callable[[ProvisionFragment], Awaitable[dict]], optional): Function that shall be called on provide (in the async eventloop). Defaults to None.
        on_unprovide (Callable[[], Awaitable[dict]], optional): Function that shall be called on unprovide (in the async eventloop). Defaults to None.
        structure_registry (StructureRegistry, optional): The structure registry to use for this Actor (used to shrink and expand inputs). Defaults to None.
    """

    def real_decorator(function_or_actor):
        # Simple bypass for now
        def wrapped_function(*args, **kwargs):
            return function_or_actor(*args, **kwargs)

        get_default_definition_registry().register(
            function_or_actor,
            structure_registry=structure_registry or get_default_structure_registry(),
            actifier= actifier,
            interface=interface,
            widgets=widgets,
            interfaces=interfaces,
            on_provide=on_provide,
            on_unprovide=on_unprovide,
            **actifier_params,
            
        )

        return wrapped_function

    return real_decorator



def create_arkitekt_folder(with_cache: bool = True):
    """Create the arkitekt folder"""
    os.makedirs(".arkitekt", exist_ok=True)
    if with_cache:
        os.makedirs(".arkitekt/cache", exist_ok=True)

    gitignore = os.path.join(".arkitekt", ".gitignore")
    if not os.path.exists(gitignore):
        with open(gitignore, "w") as f:
            f.write("# Hiding Arkitekt Credential files from git\n*.json\n*.temp\ncache/")

    return ".arkitekt"
