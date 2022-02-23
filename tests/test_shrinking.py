from typing import Dict, List, Tuple
from arkitekt.api.schema import adefine, define
from arkitekt.definition.define import prepare_definition
import pytest
from arkitekt.structures.registry import StructureRegistry, register_structure

from tests.structures import SecondSerializableObject, SerializableObject
from tests.funcs import karl_structure, complex_karl, karl, structured_gen
from arkitekt.structures.serialization.postman import (
    shrink_inputs,
    expand_outputs,
    ShrinkingError,
)
from arkitekt.structures.serialization.actor import (
    shrink_outputs,
    expand_inputs,
    ExpandingError,
)
from rath.links import compose, ShrinkingLink, DictingLink, SwitchAsyncLink
from rath.links.testing.mock import AsyncMockLink
from tests.mocks import ArkitektMockResolver
from arkitekt import Arkitekt


@pytest.fixture
def context_safe_client():

    link = compose(
        SwitchAsyncLink(),
        ShrinkingLink(),
        DictingLink(),  # after the shrinking so we can override the dicting
        AsyncMockLink(
            resolver=ArkitektMockResolver(),
        ),
    )

    return Arkitekt(link)


@pytest.fixture
def simple_registry():

    registry = StructureRegistry()

    register_structure(identifier="test", registry=registry)(SerializableObject)
    register_structure(identifier="karl", registry=registry)(SecondSerializableObject)

    return registry


async def test_shrinking(simple_registry, arkitekt_client):

    functional_definition = prepare_definition(
        structured_gen, structure_registry=simple_registry
    )

    node = await adefine(functional_definition, arkitekt=arkitekt_client)
    args, kwargs = await shrink_inputs(node, "hallo")
    assert "name" in kwargs, "Didn't contain proper key for name"


@pytest.mark.parametrize(
    ["args", "kwargs"],
    [
        ((["hallo"], {"k": 5}), {"name": "name"}),
        ((["nn", "nn"], {"k": 5}), {"name": "name"}),
        ((["nn", "nn"], {"k": 5}), {}),
    ],
)
async def test_shrinking_complex(args, kwargs, simple_registry, context_safe_client):

    definition = prepare_definition(complex_karl, structure_registry=simple_registry)

    node = await adefine(definition, arkitekt=context_safe_client)

    parsed_args, parsed_kwargs = await shrink_inputs(
        node, args, kwargs, structure_registry=simple_registry
    )
    assert "name" in parsed_kwargs, "Didn't contain proper key for name"
    assert len(parsed_args) == 2, "Args are two short"


@pytest.mark.parametrize(
    ["args", "kwargs"],
    [
        (
            ([SerializableObject(number=4)],),
            {"name": {"k": SerializableObject(number=6)}},
        ),
    ],
)
async def test_shrinking_complex_structure(
    args, kwargs, simple_registry, context_safe_client
):

    definition = prepare_definition(structured_gen, structure_registry=simple_registry)

    node = await adefine(definition, arkitekt=context_safe_client)

    parsed_args, parsed_kwargs = await shrink_inputs(
        node, args, kwargs, structure_registry=simple_registry
    )
    assert "name" in parsed_kwargs, "Didn't contain proper key for name"
    assert len(parsed_args) == 1, "Args are two short"
    assert parsed_args[0] == [4], "List Arg Converstion failed"
    assert parsed_kwargs["name"] == {"k": 6}, "List Arg Converstion failed"


@pytest.mark.parametrize(
    ["args", "kwargs"],
    [
        (([4],), {"name": {"k": 6}}),
    ],
)
async def test_expanding_complex_structure(
    args, kwargs, simple_registry, context_safe_client
):

    definition = prepare_definition(structured_gen, structure_registry=simple_registry)

    functional_node = await adefine(definition, arkitekt=context_safe_client)

    parsed_args, parsed_kwargs = await expand_inputs(
        functional_node, args, kwargs, structure_registry=simple_registry
    )
    assert "name" in parsed_kwargs, "Didn't contain proper key for name"
    assert len(parsed_args) == 1, "Args are two short"


@pytest.mark.parametrize(
    ["args", "kwargs"],
    [
        (
            ([SerializableObject(number=4)], {"k": SerializableObject(number=7)}),
            {"name": SerializableObject(number=6)},
        ),
    ],
)
async def unpack_pack(args, kwargs, simple_registry, context_safe_client):
    definition = prepare_definition(structured_gen, structure_registry=simple_registry)
    node = await adefine(definition, arkitekt=context_safe_client)

    parsed_args, parsed_kwargs = await shrink_inputs(
        node, args, kwargs, structure_registry=simple_registry
    )
    expanded_args, expanded_kwargs = await expand_inputs(
        node, parsed_args, parsed_kwargs
    )
    assert args == expanded_args, "Unpack Pack did not work"
    assert kwargs == expanded_kwargs, "Unpack Pack did not work"


async def test_shrinking_complex_error(simple_registry, context_safe_client):

    definition = prepare_definition(complex_karl, structure_registry=simple_registry)
    functional_node = await adefine(definition, arkitekt=context_safe_client)

    with pytest.raises(ShrinkingError):
        args, kwargs = await shrink_inputs(
            functional_node, ["hallo"], {"k": Dict}, structure_registry=simple_registry
        )
    with pytest.raises(ShrinkingError):

        args, kwargs = await shrink_inputs(
            functional_node, ["hallo"], 3, structure_registry=simple_registry
        )


async def test_shrinking(simple_registry, context_safe_client):
    definition = prepare_definition(karl, structure_registry=simple_registry)
    functional_node = await adefine(definition, arkitekt=context_safe_client)
    args, kwargs = await shrink_inputs(functional_node, ("hallo",), {}, simple_registry)
    assert "name" in kwargs, "Didn't contain proper key for name"


async def test_expanding(simple_registry, context_safe_client):
    definition = prepare_definition(karl, structure_registry=simple_registry)
    functional_node = await adefine(definition, arkitekt=context_safe_client)
    expanded = await expand_outputs(functional_node, ["expanded"], simple_registry)
    assert expanded == "expanded"
