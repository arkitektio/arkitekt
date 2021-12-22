from pydantic.main import BaseModel
from arkitekt.packers.structure import Structure
from arkitekt.packers.registry import (
    PackerRegistry,
    StructureOverwriteError,
    UnpackableError,
    StructureMeta,
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
from .definitions import karl, complex_karl, karl_structure, structured_gen


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


async def test_define_structured_gen():

    functional_node = define(structured_gen)
    assert isinstance(functional_node, Node), "Node is not Node"
    assert (
        functional_node.name == "Structured Karl"
    ), "Doesnt conform to standard Naming Scheme"
