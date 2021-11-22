from pydantic.main import BaseModel
from arkitekt.packers.structure import Structure
from arkitekt.packers.registry import (
    PackerRegistry,
    StructureOverwriteError,
    UnpackableError,
    register_structure,
)
from arkitekt.schema.ports import (
    DictArgPort,
    IntArgPort,
    ListArgPort,
    ListReturnPort,
    StringArgPort,
    StringKwargPort,
)
from typing import Dict, List, Tuple
from arkitekt.packers.utils import ShrinkingError, expand_outputs
from arkitekt.schema.node import Node
from arkitekt.packers import shrink_inputs, expand_inputs
from arkitekt.actors import define
import pytest


@register_structure(identifier="test")
class SerializableObject(BaseModel):
    number: int

    async def shrink(self):
        return self.number

    @classmethod
    async def expand(cls, shrinked_value):
        return cls(number=shrinked_value)


@register_structure(identifier="karl")
class SecondSerializableObject:
    async def shrink(self):
        return 5

    @classmethod
    async def expand(cls, shrinked_value):
        return cls()


def karl(rep: str, name: str = None) -> str:
    """Karl

    Karl takes a a representation and does magic stuff

    Args:
        rep (str): Nougat
        name (str, optional): Bugat

    Returns:
        Representation: The Returned Representation
    """
    return "tested"


def karl_structure(
    rep: SerializableObject, name: SerializableObject = None
) -> SecondSerializableObject:
    """Karl

    Karl takes a a representation and does magic stuff

    Args:
        rep (SerializableObject): Nougat
        name (SerializableObject, optional): Bugat

    Returns:
        SecondSerializableObject: The Returned Representation
    """
    return "tested"


def complex_karl(
    rep: List[str], nana: Dict[str, int], name: str = None
) -> Tuple[List[str], int]:
    """Complex Karl

    Nananan

    Args:
        rep (List[str]): arg
        rep (List[str]): arg2
        name (str, optional): kwarg. Defaults to None.

    Returns:
        Tuple[List[str], int]: return, return2
    """
    return ["tested"], 6


def complex_structure_call(
    rep: List[SerializableObject],
    franz: Dict[str, SecondSerializableObject],
    name: SerializableObject = None,
) -> Tuple[List[SecondSerializableObject], int]:
    """Complex Structure Call

    This is a lovely Documentatoin

    Args:
        rep (List[SerializableObject]): A List of SerializableObject
        franz (Dict[str, SecondSerializableObject]): A dictionary of SecondSerializableObject
        name (SerializableObject, optional):  A Serializable Object. Defaults to None

    Returns:
        Tuple[List[SecondSerializableObject], int]: Stuff oh stuff, Integer
    """


async def test_structure_registration():
    registry = PackerRegistry()

    @register_structure(identifier="test", registry=registry)
    class SerializableObject:
        def __init__(self, number) -> None:
            super().__init__()
            self.number = number

        async def shrink(self):
            return self.number

        @classmethod
        async def expand(cls, shrinked_value):
            return cls(shrinked_value)

    assert "test" in registry.identifierStructureMap, "Registration fails"

    with pytest.raises(StructureOverwriteError):

        @register_structure(identifier="test", registry=registry)
        class SerializableObject:
            def __init__(self, number) -> None:
                super().__init__()
                self.number = number

            async def shrink(self):
                return self.number

            @classmethod
            async def expand(cls, shrinked_value):
                return cls(shrinked_value)

    with pytest.raises(UnpackableError):

        @register_structure(identifier="karl", registry=registry)
        class SerializableObject:
            def __init__(self, number) -> None:
                super().__init__()
                self.number = number

            @classmethod
            async def expand(cls, shrinked_value):
                return cls(shrinked_value)


async def test_define():

    functional_node = define(karl)
    assert isinstance(functional_node, Node), "Node is not Node"
    assert functional_node.name == "Karl", "Doesnt conform to standard Naming Scheme"


async def test_define_complex():

    functional_node = define(complex_karl)
    assert isinstance(functional_node, Node), "Node is not Node"
    assert (
        functional_node.name == "Complex Karl"
    ), "Doesnt conform to standard Naming Scheme"
    assert len(functional_node.args) == 2, "Wrong amount of Arguments"
    assert isinstance(functional_node.args[0], ListArgPort), "Wasn't defined as a List"
    assert isinstance(functional_node.args[1], DictArgPort), "Wasn't defined as a List"
    assert isinstance(
        functional_node.args[1].child, IntArgPort
    ), "Wasn't defined as a List"
    assert isinstance(
        functional_node.args[0].child, StringArgPort
    ), "List Child wasn't a String"
    assert isinstance(
        functional_node.kwargs[0], StringKwargPort
    ), "First Kwargs is not a String"
    assert len(functional_node.returns) == 2, "Wrong amount of Returns"
    assert isinstance(
        functional_node.returns[0], ListReturnPort
    ), "Needs to Return List"


async def test_define_structure():

    functional_node = define(karl_structure)
    assert isinstance(functional_node, Node), "Node is not Node"
    assert functional_node.name == "Karl", "Doesnt conform to standard Naming Scheme"


async def test_shrinking():

    functional_node = define(karl)
    args, kwargs = await shrink_inputs(functional_node, "hallo")
    assert "name" in kwargs, "Didn't contain proper key for name"


@pytest.mark.parametrize(
    ["args", "kwargs"],
    [
        ((["hallo"], {"k": 5}), {"name": "name"}),
        ((["nn", "nn"], {"k": 5}), {"name": "name"}),
        ((["nn", "nn"], {"k": 5}), {}),
    ],
)
async def test_shrinking_complex(args, kwargs):

    functional_node = define(complex_karl)
    parsed_args, parsed_kwargs = await shrink_inputs(functional_node, *args, **kwargs)
    assert "name" in parsed_kwargs, "Didn't contain proper key for name"
    assert len(parsed_args) == 2, "Args are two short"


@pytest.mark.parametrize(
    ["args", "kwargs"],
    [
        (
            ([SerializableObject(number=4)], {"k": SecondSerializableObject()}),
            {"name": SerializableObject(number=6)},
        ),
    ],
)
async def test_shrinking_complex_structure(args, kwargs):

    functional_node = define(complex_structure_call)
    parsed_args, parsed_kwargs = await shrink_inputs(functional_node, *args, **kwargs)
    assert "name" in parsed_kwargs, "Didn't contain proper key for name"
    assert len(parsed_args) == 2, "Args are two short"
    assert parsed_args[0] == [4], "List Arg Converstion failed"
    assert parsed_args[1] == {"k": 5}, "List Arg Converstion failed"


@pytest.mark.parametrize(
    ["args", "kwargs"],
    [
        (([4], {"k": 5}), {"name": 6}),
    ],
)
async def test_expanding_complex_structure(args, kwargs):

    functional_node = define(complex_structure_call)
    parsed_args, parsed_kwargs = await expand_inputs(functional_node, args, kwargs)
    assert "name" in parsed_kwargs, "Didn't contain proper key for name"
    assert len(parsed_args) == 2, "Args are two short"


@pytest.mark.parametrize(
    ["args", "kwargs"],
    [
        (
            ([SerializableObject(number=4)], {"k": SerializableObject(number=7)}),
            {"name": SerializableObject(number=6)},
        ),
    ],
)
async def unpack_pack(args, kwargs):
    node = define(complex_structure_call)
    parsed_args, parsed_kwargs = await shrink_inputs(node, *args, **kwargs)
    expanded_args, expanded_kwargs = await expand_inputs(
        node, parsed_args, parsed_kwargs
    )
    assert args == expanded_args, "Unpack Pack did not work"
    assert kwargs == expanded_kwargs, "Unpack Pack did not work"


async def test_shrinking_complex_error():

    functional_node = define(complex_karl)
    with pytest.raises(ShrinkingError) as execinfo:
        args, kwargs = await shrink_inputs(
            functional_node, ["hallo"], {"k": Dict}, name="name"
        )
    with pytest.raises(ShrinkingError) as execinfo:
        args, kwargs = await shrink_inputs(functional_node, ["hallo"], 3, name="name")


async def test_shrinking():
    functional_node = define(karl)
    args, kwargs = await shrink_inputs(functional_node, "hallo")
    assert "name" in kwargs, "Didn't contain proper key for name"


async def test_expanding():
    functional_node = define(karl)
    expanded = await expand_outputs(functional_node, ["expanded"])
    assert expanded == "expanded"
