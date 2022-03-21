from typing import Dict
from arkitekt.api.schema import adefine
from arkitekt.definition.define import prepare_definition
import pytest
from arkitekt.structures.registry import StructureRegistry, register_structure

from tests.structures import SecondSerializableObject, SerializableObject
from tests.funcs import complex_karl, karl, structured_gen
from arkitekt.structures.serialization.postman import (
    shrink_inputs,
    expand_outputs,
    ShrinkingError,
)
from arkitekt.structures.serialization.actor import (
    expand_inputs,
)
from rath.links import compose, ShrinkingLink, DictingLink, SwitchAsyncLink
from rath.links.testing.mock import AsyncMockLink
from tests.mocks import ArkitektMockResolver
from arkitekt.rath import ArkitektRath


@pytest.fixture
def arkitekt_rath():

    link = compose(
        SwitchAsyncLink(),
        ShrinkingLink(),
        DictingLink(),  # after the shrinking so we can override the dicting
        AsyncMockLink(
            resolver=ArkitektMockResolver(),
        ),
    )

    return ArkitektRath(link=link)


@pytest.fixture
def simple_registry():

    registry = StructureRegistry()

    register_structure(identifier="test", registry=registry)(SerializableObject)
    register_structure(identifier="karl", registry=registry)(SecondSerializableObject)

    return registry


async def test_shrinking(simple_registry, arkitekt_rath):

    async with arkitekt_rath:
        functional_definition = prepare_definition(
            structured_gen, structure_registry=simple_registry
        )

        node = await adefine(functional_definition, rath=arkitekt_rath)
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
async def test_shrinking_complex(args, kwargs, simple_registry, arkitekt_rath):

    async with arkitekt_rath:
        definition = prepare_definition(
            complex_karl, structure_registry=simple_registry
        )

        node = await adefine(definition, rath=arkitekt_rath)

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
    args, kwargs, simple_registry, arkitekt_rath
):
    async with arkitekt_rath:
        definition = prepare_definition(
            structured_gen, structure_registry=simple_registry
        )

        node = await adefine(definition, rath=arkitekt_rath)

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
    args, kwargs, simple_registry, arkitekt_rath
):
    async with arkitekt_rath:
        definition = prepare_definition(
            structured_gen, structure_registry=simple_registry
        )

        functional_node = await adefine(definition, rath=arkitekt_rath)

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
async def unpack_pack(args, kwargs, simple_registry, arkitekt_rath):
    async with arkitekt_rath:
        definition = prepare_definition(
            structured_gen, structure_registry=simple_registry
        )
        node = await adefine(definition, rath=arkitekt_rath)

        parsed_args, parsed_kwargs = await shrink_inputs(
            node, args, kwargs, structure_registry=simple_registry
        )
        expanded_args, expanded_kwargs = await expand_inputs(
            node, parsed_args, parsed_kwargs
        )
        assert args == expanded_args, "Unpack Pack did not work"
        assert kwargs == expanded_kwargs, "Unpack Pack did not work"


async def test_shrinking_complex_error(simple_registry, arkitekt_rath):

    async with arkitekt_rath:
        definition = prepare_definition(
            complex_karl, structure_registry=simple_registry
        )
        functional_node = await adefine(definition, rath=arkitekt_rath)

        with pytest.raises(ShrinkingError):
            args, kwargs = await shrink_inputs(
                functional_node,
                ["hallo"],
                {"k": Dict},
                structure_registry=simple_registry,
            )
        with pytest.raises(ShrinkingError):

            args, kwargs = await shrink_inputs(
                functional_node, ["hallo"], 3, structure_registry=simple_registry
            )


async def test_shrinking(simple_registry, arkitekt_rath):

    async with arkitekt_rath:
        definition = prepare_definition(karl, structure_registry=simple_registry)
        functional_node = await adefine(definition, rath=arkitekt_rath)
        args, kwargs = await shrink_inputs(
            functional_node, ("hallo",), {}, simple_registry
        )
        assert "name" in kwargs, "Didn't contain proper key for name"


async def test_expanding(simple_registry, arkitekt_rath):
    async with arkitekt_rath:
        definition = prepare_definition(karl, structure_registry=simple_registry)
        functional_node = await adefine(definition, rath=arkitekt_rath)
        expanded = await expand_outputs(functional_node, ["expanded"], simple_registry)
        assert expanded == "expanded"
