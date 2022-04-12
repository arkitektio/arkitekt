from typing import Dict
from docstring_parser import compose
from pydantic import ValidationError
from arkitekt.structures.registry import StructureRegistry, register_structure
from arkitekt.api.schema import DefinitionInput, NodeFragment, adefine
import pytest
from .funcs import karl, complex_karl, karl_structure, structured_gen
from .structures import SecondSerializableObject, SerializableObject
from arkitekt.definition.define import prepare_definition
from .mocks import MockArkitektRath


@pytest.fixture
def simple_registry():

    registry = StructureRegistry()

    register_structure(identifier="test", registry=registry)(SerializableObject)
    register_structure(identifier="karl", registry=registry)(SecondSerializableObject)

    return registry


async def test_define(simple_registry):

    functional_definition = prepare_definition(karl, structure_registry=simple_registry)
    assert isinstance(
        functional_definition, DefinitionInput
    ), "output is not a definition"
    assert (
        functional_definition.name == "Karl"
    ), "Doesnt conform to standard Naming Scheme"


async def test_define_complex(simple_registry):

    functional_definition = prepare_definition(
        complex_karl, structure_registry=simple_registry
    )
    assert isinstance(
        functional_definition, DefinitionInput
    ), "output is not a definition"
    assert (
        functional_definition.name == "Complex Karl"
    ), "Doesnt conform to standard Naming Scheme"
    assert len(functional_definition.args) == 2, "Wrong amount of Arguments"
    assert (
        functional_definition.args[0].typename == "ListArgPort"
    ), "Wasn't defined as a List"
    assert (
        functional_definition.args[1].typename == "DictArgPort"
    ), "Wasn't defined as a Dict"
    assert (
        functional_definition.args[1].child.typename == "IntArgPort"
    ), "Child of List is not of type IntArgPort"
    assert (
        functional_definition.args[0].child.typename == "StringArgPort"
    ), "Child of Dict is not of type StringArgPort"
    assert (
        functional_definition.kwargs[0].typename == "StringKwargPort"
    ), "Kwarg wasn't defined as a StringKwargPort"
    assert len(functional_definition.returns) == 2, "Wrong amount of Returns"
    assert (
        functional_definition.returns[0].typename == "ListReturnPort"
    ), "Needs to Return List"


async def test_define_structure(simple_registry):

    functional_definition = prepare_definition(
        karl_structure, structure_registry=simple_registry
    )
    assert isinstance(
        functional_definition, DefinitionInput
    ), "output is not a definition"
    assert (
        functional_definition.name == "Karl"
    ), "Doesnt conform to standard Naming Scheme"


async def test_define_structured_gen(simple_registry):

    functional_definition = prepare_definition(
        structured_gen, structure_registry=simple_registry
    )
    assert isinstance(functional_definition, DefinitionInput), "Node is not Node"
    assert (
        functional_definition.name == "Structured Karl"
    ), "Doesnt conform to standard Naming Scheme"


@pytest.fixture
def arkitekt_rath():

    return MockArkitektRath()


async def test_define_to_node_gen(simple_registry, arkitekt_rath):

    async with arkitekt_rath:
        functional_definition = prepare_definition(
            structured_gen, structure_registry=simple_registry
        )

        node = await adefine(functional_definition)

        assert isinstance(node, NodeFragment), "Node is not Node"
        assert (
            node.name == "Structured Karl"
        ), "Doesnt conform to standard Naming Scheme"
        assert (
            node.name == "Structured Karl"
        ), "Doesnt conform to standard Naming Scheme"
        assert len(node.args) == 1, "Wrong amount of Arguments"
        assert len(node.kwargs) == 1, "Wrong amount of Kwargs"
        assert len(node.returns) == 2, "Wrong amount of Returns"
        assert node.args[0].typename == "ListArgPort", "Wasn't defined as a List"
        assert (
            node.args[0].child.typename == "StructureArgPort"
        ), "Wasn't defined as a List"
        assert node.args[0].child.identifier == "test", "Wasn't indtifier on test"


async def test_define_to_node_complex(simple_registry, arkitekt_rath):

    async with arkitekt_rath:

        functional_definition = prepare_definition(
            complex_karl, structure_registry=simple_registry
        )

        node = await adefine(functional_definition, rath=arkitekt_rath)

        assert isinstance(node, NodeFragment), "Node is not Node"
        assert node.name == "Complex Karl", "Doesnt conform to standard Naming Scheme"
        assert len(node.args) == 2, "Wrong amount of Arguments"
        assert node.args[0].typename == "ListArgPort", "Wasn't defined as a List"
        assert node.args[1].typename == "DictArgPort", "Wasn't defined as a Dict"
        assert (
            node.args[1].child.typename == "IntArgPort"
        ), "Child of List is not of type IntArgPort"
        assert (
            node.args[0].child.typename == "StringArgPort"
        ), "Child of Dict is not of type StringArgPort"
        assert (
            node.kwargs[0].typename == "StringKwargPort"
        ), "Kwarg wasn't defined as a StringKwargPort"
        assert len(functional_definition.returns) == 2, "Wrong amount of Returns"
        assert node.returns[0].typename == "ListReturnPort", "Needs to Return List"


async def test_define_node_has_nested_type(simple_registry, arkitekt_rath):
    def x(a: Dict[str, Dict[str, int]]) -> int:
        """Nanana

        sss

        Args:
            a (Dict[str, Dict[str, int]]): _description_
        """
        return 5

    functional_definition = prepare_definition(x, structure_registry=simple_registry)

    async with arkitekt_rath:
        node = await adefine(functional_definition, rath=arkitekt_rath)
