from arkitekt.structures.registry import StructureRegistry, register
from arkitekt.api.schema import (
    DefinitionInput,
)
import pytest
from .funcs import karl, complex_karl, karl_structure, structured_gen
from .structures import SecondSerializableObject, SerializableObject
from arkitekt.definition.define import prepare_definition


@pytest.fixture
def simple_registry():

    registry = StructureRegistry()

    register(identifier="test", registry=registry)(SerializableObject)
    register(identifier="karl", registry=registry)(SecondSerializableObject)

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
