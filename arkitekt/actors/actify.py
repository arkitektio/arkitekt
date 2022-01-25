from enum import Enum
from os import strerror
from arkitekt.actors.base import Actor
from arkitekt.actors.functional import (
    FunctionalFuncActor,
    FunctionalGenActor,
    FunctionalThreadedFuncActor,
    FunctionalThreadedGenActor,
)

import inspect
from inspect import signature, Parameter
from docstring_parser import parse
import logging
import inflection

from arkitekt.serialization.registry import StructureRegistry

logger = logging.getLogger(__name__)
from typing import Callable, Dict, List
import inspect


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


async def async_none(message):
    return None


def actify(
    function_or_actor,
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
        "on_provide": on_provide if on_provide else async_none,
        "on_unprovide": on_unprovide if on_unprovide else async_none,
        "structure_registry": structure_registry,
    }

    if is_coroutine:
        return lambda: FunctionalFuncActor(**actor_attributes)
    elif is_asyncgen:
        return lambda: FunctionalGenActor(**actor_attributes)
    elif is_generatorfunction:
        return lambda: FunctionalThreadedGenActor(**actor_attributes)
    elif is_function or is_method:
        return lambda: FunctionalThreadedFuncActor(**actor_attributes)
    else:
        raise NotImplementedError("No way of converting this to a function")
