from arkitekt.actors.base import Actor
from arkitekt.actors.functional import (
    FunctionalFuncActor,
    FunctionalGenActor,
    FunctionalThreadedFuncActor,
    FunctionalThreadedGenActor,
)

import inspect
from arkitekt.structures.registry import StructureRegistry
from typing import Callable, Optional
import inspect
from .types import ActorBuilder


class ConversionError(Exception):
    pass


class NonConvertableType(ConversionError):
    pass


def isactor(type):
    try:
        if issubclass(type, Actor):
            return True
        else:
            return False
    except Exception as e:
        return False


async def async_none_provide(prov, template):
    return None


async def async_none_unprovide():
    return None


def actify(
    function_or_actor,
    builder: Optional[ActorBuilder] = None,
    bypass_shrink=False,
    bypass_expand=False,
    on_provide=None,
    on_unprovide=None,
    actor_name=None,
    structure_registry: StructureRegistry = None,
    **params,
) -> Callable[[], Actor]:

    if isactor(function_or_actor):
        return function_or_actor

    actor_name = (
        actor_name or f"GeneratedActor{function_or_actor.__name__.capitalize()}"
    )

    is_coroutine = inspect.iscoroutinefunction(function_or_actor)
    is_asyncgen = inspect.isasyncgenfunction(function_or_actor)
    is_method = inspect.ismethod(function_or_actor)

    is_generatorfunction = inspect.isgeneratorfunction(function_or_actor)
    is_function = inspect.isfunction(function_or_actor)

    actor_attributes = {
        "assign": function_or_actor,
        "expand_inputs": not bypass_expand,
        "shrink_outputs": not bypass_shrink,
        "provide": on_provide if on_provide else async_none_provide,
        "unprovide": on_unprovide if on_unprovide else async_none_unprovide,
        "structure_registry": structure_registry,
    }

    if builder:
        assert hasattr(builder, "build_actor"), "Builder must have a build_actor method"
        instance = builder(**actor_attributes)
        return lambda provision, transport: instance.build_actor(provision, transport)

    if is_coroutine:
        return lambda provision, transport: FunctionalFuncActor(
            provision=provision, transport=transport, **actor_attributes
        )
    elif is_asyncgen:
        return lambda provision, transport: FunctionalGenActor(
            provision=provision, transport=transport, **actor_attributes
        )
    elif is_generatorfunction:
        return lambda provision, transport: FunctionalThreadedGenActor(
            provision=provision, transport=transport, **actor_attributes
        )
    elif is_function or is_method:
        return lambda provision, transport: FunctionalThreadedFuncActor(
            provision=provision, transport=transport, **actor_attributes
        )
    else:
        raise NotImplementedError("No way of converting this to a function")
