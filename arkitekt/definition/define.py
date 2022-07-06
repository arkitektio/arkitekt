from enum import Enum
from typing import Callable
import inflection
from arkitekt.api.schema import (
    ArgPortInput,
    DefinitionInput,
    KwargPortInput,
    NodeTypeInput,
    PortType,
    PortTypeInput,
    ReturnPortInput,
)
import inspect
from docstring_parser import parse
from arkitekt.definition.errors import DefinitionError

from arkitekt.structures.registry import (
    StructureRegistry,
)


def convert_arg_to_argport(
    cls, key, registry: StructureRegistry, widget=None
) -> ArgPortInput:
    """
    Convert a class to an ArgPort
    """

    widget = widget or registry.get_widget_input(cls)

    if hasattr(cls, "_name"):
        # We are dealing with a Typing Var?
        if cls._name == "List":
            child = convert_arg_to_argport(cls.__args__[0], "omit", registry)
            return ArgPortInput(
                type=PortType.LIST,
                widget=widget,
                key=key,
                child=child.dict(exclude={"key"}),
            )

        if cls._name == "Dict":
            child = convert_arg_to_argport(cls.__args__[1], "omit", registry)
            return ArgPortInput(
                type=PortType.DICT,
                widget=widget,
                key=key,
                child=child.dict(exclude={"key"}),
            )

    if inspect.isclass(cls):
        # Generic Cases

        if issubclass(cls, bool):
            return ArgPortInput(
                type=PortType.BOOL, widget=widget, key=key
            )  # catch bool is subclass of int
        if issubclass(cls, Enum):
            return ArgPortInput(
                type=PortType.ENUM,
                widget=widget,
                key=key,
                options={key: value._value_ for key, value in cls.__members__.items()},
            )
        if issubclass(cls, int):
            return ArgPortInput(type=PortType.INT, widget=widget, key=key)
        if issubclass(cls, str):
            return ArgPortInput(type=PortType.STRING, widget=widget, key=key)

    identifier = registry.get_identifier_for_structure(cls)
    return ArgPortInput(
        type=PortType.STRUCTURE,
        identifier=identifier,
        widget=widget,
        key=key,
    )


def convert_kwarg_to_kwargport(
    cls, key, registry: StructureRegistry, widget=None, default=None
) -> ArgPortInput:
    """
    Convert a class to an ArgPort
    """
    widget = widget or registry.get_widget_input(cls)

    if hasattr(cls, "_name"):
        # We are dealing with a Typing Var?
        if cls._name == "List":
            child = convert_kwarg_to_kwargport(cls.__args__[0], "omit", registry)
            return KwargPortInput(
                type=PortTypeInput.LIST,
                widget=widget,
                key=key,
                child=child.dict(exclude={"key"}),
                default=default,
            )

        if cls._name == "Dict":
            child = convert_kwarg_to_kwargport(cls.__args__[1], "omit", registry)
            return KwargPortInput(
                type=PortTypeInput.DICT,
                widget=widget,
                key=key,
                child=child.dict(exclude={"key"}),
                default=default,
            )

    if inspect.isclass(cls):
        # Generic Cases

        if issubclass(cls, bool) or isinstance(default, bool):
            t = KwargPortInput(
                type=PortType.BOOL, widget=widget, key=key, default=default
            )  # catch bool is subclass of int
            return t

        if issubclass(cls, Enum) or isinstance(default, Enum):
            return KwargPortInput(
                type=PortType.ENUM,
                widget=widget,
                key=key,
                options={key: value._value_ for key, value in cls.__members__.items()},
                default=default,
            )
        if issubclass(cls, int) or isinstance(default, int):
            return KwargPortInput(
                type=PortType.INT, widget=widget, key=key, default=default
            )
        if issubclass(cls, str) or isinstance(default, str):
            return KwargPortInput(
                type=PortType.STRING,
                widget=widget,
                key=key,
                default=default,
            )

    identifier = registry.get_identifier_for_structure(cls)

    return KwargPortInput(
        type=PortType.STRUCTURE,
        identifier=identifier,
        widget=widget,
        key=key,
        default=default,
    )


def convert_return_to_returnport(
    cls, key: str, registry: StructureRegistry, widget=None
) -> ReturnPortInput:
    """
    Convert a class to an ArgPort
    """
    widget = widget or registry.get_returnwidget_input(cls)

    if hasattr(cls, "_name"):
        # We are dealing with a Typing Var?
        if cls._name == "List":
            child = convert_return_to_returnport(cls.__args__[0], "omit", registry)
            return ReturnPortInput(
                type=PortType.LIST,
                key=key,
                child=child.dict(exclude={"key"}),
            )

        if cls._name == "Dict":
            child = convert_return_to_returnport(cls.__args__[1], "omit", registry)
            return ReturnPortInput(
                type=PortType.DICT,
                key=key,
                child=child.dict(exclude={"key"}),
            )

    if inspect.isclass(cls):
        # Generic Cases

        if issubclass(cls, bool):
            return ReturnPortInput(
                type=PortType.BOOL, key=key
            )  # catch bool is subclass of int
        if issubclass(cls, Enum):
            return ReturnPortInput(
                type=PortType.ENUM,
                key=key,
                options={key: value._value_ for key, value in cls.__members__.items()},
            )
        if issubclass(cls, int):
            return ReturnPortInput(
                type=PortType.INT,
                key=key,
            )
        if issubclass(cls, str):
            return ReturnPortInput(
                type=PortType.STRING,
                key=key,
            )

    identifier = registry.get_identifier_for_structure(cls)

    return ReturnPortInput(
        type=PortType.STRUCTURE,
        identifier=identifier,
        key=key,
        widget=widget,
    )


def prepare_definition(
    function: Callable,
    package=None,
    interface=None,
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
                    convert_arg_to_argport(cls, key, structure_registry, widget=widget)
                )
            else:
                kwargs.append(
                    convert_kwarg_to_kwargport(
                        cls,
                        key,
                        structure_registry,
                        widget=widget,
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
                for index, cls in enumerate(function_outs_annotation.__args__):
                    widget = widgets.get(f"return{index}", None)
                    returns.append(
                        convert_return_to_returnport(
                            cls, f"return{index}", structure_registry
                        )
                    )
            except Exception as e:
                raise DefinitionError(
                    f"Could not convert Return of function {function.__name__} to ArgPort: {cls}"
                ) from e
        else:
            try:
                widget = widgets.get(f"return0", None)
                returns.append(
                    convert_return_to_returnport(
                        function_outs_annotation,
                        f"return0",
                        structure_registry,
                        widget=widget,
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
            widget = widgets.get(f"return0", None)
            returns.append(
                convert_return_to_returnport(
                    function_outs_annotation,
                    "return0",
                    structure_registry,
                    widget=widget,
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
    interface = interface or inflection.underscore(
        function.__name__
    )  # convert this to camelcase
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

    x = DefinitionInput(
        **{
            "name": name,
            "interface": interface,
            "package": package,
            "description": description,
            "args": args,
            "kwargs": kwargs,
            "returns": returns,
            "type": NodeTypeInput.GENERATOR if is_generator else NodeTypeInput.FUNCTION,
            "interfaces": interfaces,
        }
    )

    print(x)

    return x
