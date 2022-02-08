from enum import Enum
from typing import Callable, List
import inflection
from pydantic import BaseModel
from arkitekt.api.schema import (
    ArgPortInput,
    DefinitionInput,
    KwargPortInput,
    NodeTypeInput,
    ReturnPortInput,
)
import inspect
from docstring_parser import parse
from arkitekt.definition.errors import DefinitionError

from arkitekt.structures.registry import (
    StructureRegistry,
)


def convert_arg_to_argport(
    cls, registry: StructureRegistry, widget=None, key=None
) -> ArgPortInput:
    """
    Convert a class to an ArgPort
    """

    widget = widget or registry.get_widget_input(cls)

    if hasattr(cls, "_name"):
        # We are dealing with a Typing Var?
        if cls._name == "List":
            child = convert_arg_to_argport(cls.__args__[0], registry)
            return ArgPortInput(
                typename="ListArgPort", widget=widget, key=key, child=child
            )

        if cls._name == "Dict":
            child = convert_arg_to_argport(cls.__args__[1], registry)
            return ArgPortInput(
                typename="DictArgPort", widget=widget, key=key, child=child
            )

    if inspect.isclass(cls):
        # Generic Cases

        if issubclass(cls, bool):
            return ArgPortInput(
                typename="BoolArgPort", widget=widget, key=key
            )  # catch bool is subclass of int
        if issubclass(cls, Enum):
            return ArgPortInput(
                typename="EnumArgPort",
                widget=widget,
                key=key,
                options={key: value._value_ for key, value in cls.__members__.items()},
            )
        if issubclass(cls, int):
            return ArgPortInput(typename="IntArgPort", widget=widget, key=key)
        if issubclass(cls, str):
            return ArgPortInput(typename="StringArgPort", widget=widget, key=key)

    identifier = registry.get_identifier_for_structure(cls)

    return ArgPortInput(
        typename="StructureArgPort",
        identifier=identifier,
        widget=widget,
        key=key,
    )


def convert_kwarg_to_kwargport(
    cls, registry: StructureRegistry, widget=None, key=None, default=None
) -> ArgPortInput:
    """
    Convert a class to an ArgPort
    """
    widget = widget or registry.get_widget_input(cls)

    if hasattr(cls, "_name"):
        # We are dealing with a Typing Var?
        if cls._name == "List":
            child = convert_kwarg_to_kwargport(cls.__args__[0], registry)
            return KwargPortInput(
                typename="ListKwargPort",
                widget=widget,
                key=key,
                child=child,
                defaultList=default,
            )

        if cls._name == "Dict":
            child = convert_kwarg_to_kwargport(cls.__args__[1], registry)
            return KwargPortInput(
                typename="DictKwargPort",
                widget=widget,
                key=key,
                child=child,
                defaultDict=default,
            )

    if inspect.isclass(cls):
        # Generic Cases

        if issubclass(cls, bool) or isinstance(default, bool):
            return KwargPortInput(
                typename="BoolKwargPort", widget=widget, key=key, defaultBool=default
            )  # catch bool is subclass of int
        if issubclass(cls, Enum) or isinstance(default, Enum):
            return KwargPortInput(
                typename="EnumKwargPort",
                widget=widget,
                key=key,
                options={key: value._value_ for key, value in cls.__members__.items()},
                defaultEnum=default,
            )
        if issubclass(cls, int) or isinstance(default, int):
            return KwargPortInput(
                typename="IntKwargPort", widget=widget, key=key, defaultInt=default
            )
        if issubclass(cls, str) or isinstance(default, str):
            return KwargPortInput(
                typename="StringKwargPort",
                widget=widget,
                key=key,
                defaultString=default,
            )

    identifier = registry.get_identifier_for_structure(cls)

    return KwargPortInput(
        typename="StructureKwargPort",
        identifier=identifier,
        widget=widget,
        key=key,
        defaultID=default,
    )


def convert_return_to_returnport(
    cls, registry: StructureRegistry, key=None, default=None
) -> ReturnPortInput:
    """
    Convert a class to an ArgPort
    """

    if hasattr(cls, "_name"):
        # We are dealing with a Typing Var?
        if cls._name == "List":
            child = convert_return_to_returnport(cls.__args__[0], registry)
            return ReturnPortInput(
                typename="ListReturnPort",
                key=key,
                child=child,
                defaultList=default,
            )

        if cls._name == "Dict":
            child = convert_return_to_returnport(cls.__args__[1], registry)
            return ReturnPortInput(
                typename="DictReturnPort",
                key=key,
                child=child,
                defaultDict=default,
            )

    if inspect.isclass(cls):
        # Generic Cases

        if issubclass(cls, bool):
            return ReturnPortInput(
                typename="BoolReturnPort", key=key
            )  # catch bool is subclass of int
        if issubclass(cls, Enum):
            return ReturnPortInput(
                typename="EnumReturnPort",
                key=key,
                options={key: value._value_ for key, value in cls.__members__.items()},
            )
        if issubclass(cls, int):
            return ReturnPortInput(
                typename="IntReturnPort",
                key=key,
            )
        if issubclass(cls, str):
            return ReturnPortInput(
                typename="StringReturnPort",
                key=key,
            )

    identifier = registry.get_identifier_for_structure(cls)

    return ReturnPortInput(
        typename="StructureReturnPort",
        identifier=identifier,
        key=key,
    )


def prepare_definition(
    function: Callable,
    widgets={},
    allow_empty_doc=False,
    interfaces=[],
    structure_registry: StructureRegistry = None,
) -> DefinitionInput:
    """Define

    Define a functions in the context of arnheim and
    return it as a Node. Attention this node is not yet
    hosted on Arkitekt (doesn't have an id). So make sure
    to save this node before calling it anywhere

    Args:
        function (): The function you want to define
    """

    assert structure_registry is not None, "You need to pass a StructureRegistry"

    is_generator = inspect.isasyncgenfunction(function) or inspect.isgeneratorfunction(
        function
    )

    sig = inspect.signature(function)

    # Generate Args and Kwargs from the Annotation
    args = []
    kwargs = []
    returns = []

    function_ins_annotation = sig.parameters
    for key, value in function_ins_annotation.items():

        widget = widgets.get(key, None)
        cls = value.annotation

        try:
            if value.default == inspect.Parameter.empty:
                # This Parameter is an Argument
                args.append(
                    convert_arg_to_argport(
                        cls, structure_registry, widget=widget, key=key
                    )
                )
            else:
                kwargs.append(
                    convert_kwarg_to_kwargport(
                        cls,
                        structure_registry,
                        widget=widget,
                        key=key,
                        default=value.default,
                    )
                )
        except Exception as e:
            raise DefinitionError(
                f"Could not convert Argument of function {function.__name__} to ArgPort: {value}"
            ) from e

    function_outs_annotation = sig.return_annotation

    if hasattr(function_outs_annotation, "_name"):

        if function_outs_annotation._name == "Tuple":
            try:
                for cls in function_outs_annotation.__args__:
                    returns.append(
                        convert_return_to_returnport(cls, structure_registry)
                    )
            except Exception as e:
                raise DefinitionError(
                    f"Could not convert Return of function {function.__name__} to ArgPort: {cls}"
                ) from e
        else:
            try:
                returns.append(
                    convert_return_to_returnport(
                        function_outs_annotation, structure_registry
                    )
                )  # Other types will be converted to normal lists and shit
            except Exception as e:
                raise DefinitionError(
                    f"Could not convert Return of function {function.__name__} to ArgPort: {function_outs_annotation}"
                ) from e
    else:
        # We are dealing with a non tuple return
        if function_outs_annotation is None:
            pass

        elif function_outs_annotation.__name__ != "_empty":  # Is it not empty
            returns.append(
                convert_return_to_returnport(
                    function_outs_annotation, structure_registry
                )
            )

    # Documentation Parsing

    # Docstring Parser to help with descriptions
    docstring = parse(function.__doc__)
    if docstring.long_description is None:
        assert (
            allow_empty_doc is not False
        ), f"We don't allow empty documentation for function {function.__name__}. Please Provide"

    name = docstring.short_description or function.__name__
    interface = inflection.underscore(function.__name__)  # convert this to camelcase
    description = docstring.long_description or "No Description"

    doc_param_map = {
        param.arg_name: {
            "description": param.description
            if not param.description.startswith("[")
            else None,
        }
        for param in docstring.params
    }

    if docstring.returns:
        return_description = docstring.returns.description
        seperated_list = return_description.split(",")
        assert len(returns) == len(
            seperated_list
        ), f"Length of Description and Returns not Equal: If you provide a Return Annotation make sure you seperate the description for each port with ',' Return Description {return_description} Returns: {returns}"
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

    return DefinitionInput(
        **{
            "name": name,
            "interface": interface,
            "package": "test",  # TODO: IMplement correctly
            "description": description,
            "args": args,  # exclude={"typename"} for input?
            "kwargs": kwargs,
            "returns": returns,
            "type": NodeTypeInput.GENERATOR if is_generator else NodeTypeInput.FUNCTION,
            "interfaces": interfaces,
        }
    )
