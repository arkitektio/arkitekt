from typing import Dict, List, Tuple
from arkitekt.packers.utils import ShrinkingError, expand_outputs
from arkitekt.packers import shrink_inputs, expand_inputs
from arkitekt.actors import define
import pytest

from tests.structures import SecondSerializableObject, SerializableObject
from .definitions import karl_structure, complex_karl, karl, structured_gen


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
            ([SerializableObject(number=4)],),
            {"name": {"k": SerializableObject(number=6)}},
        ),
    ],
)
async def test_shrinking_complex_structure(args, kwargs):

    functional_node = define(structured_gen)
    parsed_args, parsed_kwargs = await shrink_inputs(functional_node, *args, **kwargs)
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
async def test_expanding_complex_structure(args, kwargs):

    functional_node = define(structured_gen)
    parsed_args, parsed_kwargs = await expand_inputs(functional_node, args, kwargs)
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
async def unpack_pack(args, kwargs):
    node = define(structured_gen)
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
