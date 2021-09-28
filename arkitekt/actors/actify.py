from os import strerror
from arkitekt.packers.transpilers.base import Transpiler
from arkitekt.actors.base import Actor
from arkitekt.packers.structure import Structure
from arkitekt.schema.node import Node
from arkitekt.schema.enums import NodeType
from arkitekt.schema.ports import ArgPort, DictArgPort, DictKwargPort, DictReturnPort, IntArgPort, IntKwargPort, IntReturnPort, KwargPort, ListArgPort, ListKwargPort, ListReturnPort, ReturnPort, StringArgPort, StringKwargPort, StringReturnPort, StructureArgPort, StructureKwargPort, StructureReturnPort
from arkitekt.actors.functional import FunctionalFuncActor, FunctionalGenActor, FunctionalThreadedFuncActor, FunctionalThreadedGenActor
from arkitekt.packers.transpilers.registry import get_transpiler_registry

import inspect
from inspect import signature, Parameter
from docstring_parser import parse
import logging
import inflection
logger = logging.getLogger(__name__)
from typing import Dict, List
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


def guard_is_structure(cls):
    if not inspect.ismethod(cls.get_identifier): raise NonConvertableType(f"Could not convert {cls.__name__} to Port: Please implement a classmethod get_identifier or decorate {cls.__name__} with register_structure(identifier='UNIQUEIDENTIFIER)")


def convert_arg_to_argport(cls, **kwargs) -> ArgPort:
    # Typing Support
    if hasattr(cls, "_name"):
        # We are dealing with a Typing Var?
        if cls._name == "List":
            child = convert_arg_to_argport(cls.__args__[0])
            return ListArgPort.from_params(**kwargs, child=child.dict(), ) # We have to call the dict format here as we want the public alias __typename in the intializer
            
        if cls._name == "Dict":
            child = convert_arg_to_argport(cls.__args__[1])
            return DictArgPort.from_params(**kwargs, child=child.dict(), ) # We have to

    if inspect.isclass(cls):
        # Generic Cases
        if issubclass(cls, int): return IntArgPort.from_params(**kwargs)
        if issubclass(cls, str): return StringArgPort.from_params(**kwargs)

        # Custom Cases
        # Structures are a way to implement packing and unpacking of non generic types
        # These can be imported with packages and are registered automatically registered by subclassing Structure
        if hasattr(cls, "get_identifier") and inspect.ismethod(cls.get_identifier):
            return StructureArgPort.from_params(identifier=cls.get_identifier(),**kwargs)
        else:
            transpiler = get_transpiler_registry().get_transpiler_for_type(cls)
            return StructureArgPort.from_params(identifier=transpiler.structure.get_identifier(),transpile=transpiler.type_name, **kwargs)
            
    


    raise ConversionError(f"No Factory for Arg Type {cls.__name__} Conversion found")
            



def convert_kwarg_to_kwargport(cls, **kwargs):
    # Generic Cases
    # Typing Support
    if hasattr(cls, "_name"):
        # We are dealing with a Typing Var?
        if cls._name == "List":
            child = convert_kwarg_to_kwargport(cls.__args__[0])
            return ListKwargPort.from_params(**kwargs, child=child.dict()) # We have to call the dict format here as we want the public alias __typename in the intializer
            
        if cls._name == "Dict":
            child = convert_kwarg_to_kwargport(cls.__args__[1])
            return DictKwargPort.from_params(**kwargs, child=child.dict()) # We have to call the dict format here as we want the public alias __typename in the intializer
    
    if inspect.isclass(cls):
        # Generic Cases
        if issubclass(cls, int): return IntKwargPort.from_params(**kwargs)
        if issubclass(cls, str): return StringKwargPort.from_params(**kwargs)

        # Custom Cases
        # Structures are a way to implement packing and unpacking of non generic types
        # These can be imported with packages and are registered automatically registered by subclassing Structure
        if hasattr(cls, "get_identifier") and inspect.ismethod(cls.get_identifier):
            return StructureKwargPort.from_params(identifier=cls.get_identifier(), **kwargs)
        else:
            transpiler = get_transpiler_registry().get_transpiler_for_type(cls)
            return StructureKwargPort.from_params(identifier=transpiler.structure.get_identifier(), transpile=transpiler.type_name, **kwargs)


    raise ConversionError(f"No Factory for Arg Type {cls.__name__} Conversion found")

def convert_return_to_returnport(cls, **kwargs):
    # Typing Support
    if hasattr(cls, "_name"):
        # We are dealing with a Typing Var?
        if cls._name == "List":
            child = convert_return_to_returnport(cls.__args__[0])
            return ListReturnPort.from_params(**kwargs, child=child.dict()) # We have to call the dict format here as we want the public alias __typename in the intializer
            
        if cls._name == "Dict":
            child = convert_return_to_returnport(cls.__args__[1])
            return DictReturnPort.from_params(**kwargs, child=child.dict()) # We ha

    # Generic Cases
    if inspect.isclass(cls):
        # Generic Cases
        if issubclass(cls, int): return IntReturnPort.from_params(**kwargs)
        if issubclass(cls, str): return StringReturnPort.from_params(**kwargs)

        # Custom Cases
        # Structures are a way to implement packing and unpacking of non generic types
        # These can be imported with packages and are registered automatically registered by subclassing Structure
        if hasattr(cls, "get_identifier") and inspect.ismethod(cls.get_identifier):
            return StructureReturnPort.from_params(identifier=cls.get_identifier(), **kwargs)
        else:
            transpiler = get_transpiler_registry().get_transpiler_for_type(cls)
            return StructureReturnPort.from_params(identifier=transpiler.structure.get_identifier(), transpile=transpiler.type_name, **kwargs)

    

    raise ConversionError(f"No Factory for Arg Type {cls.__name__} Conversion found")







def define(function, widgets={}, allow_empty_doc=False) -> Node:
    """Define

    Define a functions in the context of arnheim and
    return it as a Node.

    Args:
        function (): The function you want to define
    """

    is_generator = inspect.isasyncgenfunction(function) or inspect.isgeneratorfunction(function)

    sig = signature(function)
    # Generate Args and Kwargs from the Annotation
    args = []
    kwargs = []
    returns = []


    function_inputs = sig.parameters
    for key, value in function_inputs.items():
        widget = widgets.get(key, None)
        cls = value.annotation

        if value.default == Parameter.empty:
            # This Parameter is an Argument
            args.append(convert_arg_to_argport(cls, widget=widget, key=key))
        else:
            kwargs.append(convert_kwarg_to_kwargport(cls, widget=widget, key=key, default=value.default))


    function_output = sig.return_annotation
    try:
        # Raises type error if we use it with a class but needed here because typing is actually not a class but an Generic Alias :rolling_eyes::
        if function_output._name == "Tuple":
              for cls in function_output.__args__:
                  returns.append(convert_return_to_returnport(cls))

        returns.append(convert_return_to_returnport(cls)) # Other types will be converted to normal lists and shit

    except AttributeError:
        if function_output.__name__ != "_empty": # Is it not empty
            returns.append(convert_return_to_returnport(function_output))

    # Documentation Parsing 

    # Docstring Parser to help with descriptions
    docstring = parse(function.__doc__)
    if docstring.long_description is None:
        assert allow_empty_doc is not False, f"We don't allow empty documentation for function {function.__name__}. Please Provide"
        logger.warn(f"Allowing empty Documentatoin. Please consider providing a documentation for function {function.__name__}")


    name = docstring.short_description or function.__name__
    interface = inflection.underscore(name) # convert this to camelcase
    description = docstring.long_description or "No Description"

    doc_param_map = {param.arg_name: {
        "description": param.description if not param.description.startswith("[") else None,
    } for param in docstring.params}

    if docstring.returns:
        return_description = docstring.returns.description
        seperated_list = return_description.split(",")
        assert len(returns) == len(seperated_list), f"Length of Description and Returns not Equal: If you provide a Return Annotation make sure you seperate the description for each port with ',' Return Description {return_description} Returns: {returns}"
        for index, doc in enumerate(seperated_list):
            returns[index].description = doc


    # TODO: Update with documentatoin.... (Set description for portexample)
    for port in args:
        if port.key in doc_param_map:
            updates = doc_param_map[port.key]
            port.description = updates["description"] or port.description

    for port in kwargs:
        if port.key in doc_param_map:
            updates = doc_param_map[port.key]
            port.description = updates["description"] or port.description

    return Node(**{
        "name": name,
        "interface": interface,
        "package": "test", #TODO: IMplement correctly
        "description" : description,
        "args" : [arg.dict() for arg in args], #exclude={"typename"} for input?
        "kwargs" : [kwarg.dict() for kwarg in kwargs],
        "returns" : [re.dict() for re in returns],
        "type" : NodeType.GENERATOR if is_generator else NodeType.FUNCTION
    })


async def async_none(self, message):
    return None


def actify(function_or_actor, bypass_shrink=False, bypass_expand=False, transpilers: Dict[str, Transpiler] = None, on_provide=None, on_unprovide=None, **params):
    if isactor(function_or_actor): return function_or_actor
    is_method = inspect.ismethod(function_or_actor)

    actor_name = f"GeneratedActor{function_or_actor.__name__.capitalize()}"


    is_coroutine = inspect.iscoroutinefunction(function_or_actor)
    is_asyncgen = inspect.isasyncgenfunction(function_or_actor)

    is_generatorfunction = inspect.isgeneratorfunction(function_or_actor)
    is_function = inspect.isfunction(function_or_actor)
    print(on_provide)
    class_attributes = {
        "assign": staticmethod(function_or_actor),
        "expand_inputs": not bypass_expand,
        "shrink_outputs":  not bypass_shrink,
        "transpilers": transpilers,
        "on_provide": on_provide if on_provide else async_none,
        "on_unprovide": on_unprovide if on_unprovide else async_none,
    }

    if is_coroutine:
        return type(actor_name,(FunctionalFuncActor,), class_attributes)
    elif is_asyncgen:
        return  type(actor_name,(FunctionalGenActor,), class_attributes)
    elif is_generatorfunction:
        return type(actor_name, (FunctionalThreadedGenActor,),class_attributes)
    elif is_function:
        return type(actor_name,(FunctionalThreadedFuncActor,), class_attributes)
    else:
        raise NotImplementedError("No way of converting this to a function")


