from typing import Any, Dict, List
from async_timeout import asyncio
from arkitekt.api.schema import NodeFragment
from arkitekt.structures.errors import ShrinkingError, ExpandingError
from arkitekt.structures.registry import StructureRegistry


async def expand_inputs(
    node: NodeFragment,
    args: List[Any],
    kwargs: Dict[str, Any],
    structure_registry: StructureRegistry,
):
    """Expand

    Args:
        node (NodeFragment): [description]
        args (List[Any]): [description]
        kwargs (List[Any]): [description]
        registry (Registry): [description]
    """

    expanded_args = []

    try:
        expanded_args = await asyncio.gather(
            *[
                port.cause_expand(arg, structure_registry)
                for port, arg in zip(node.args, args)
            ]
        )
    except Exception as e:
        raise ExpandingError(
            f"Couldn't expand Arguments {args} with {node.args}"
        ) from e

    try:
        expanded_kwargs = {
            port.key: await port.cause_expand(
                kwargs.get(port.key, None), structure_registry
            )
            for port in node.kwargs
        }
    except Exception as e:
        raise ExpandingError(
            f"Couldn't expand Kwargs {kwargs}  with {node.kwargs}"
        ) from e

    return expanded_args, expanded_kwargs


async def shrink_outputs(
    node: NodeFragment,
    returns: List[Any],
    structure_registry: StructureRegistry,
):
    """Expand

    Args:
        node (NodeFragment): [description]
        args (List[Any]): [description]
        kwargs (List[Any]): [description]
        registry (Registry): [description]
    """
    if returns is None:
        returns = ()
    if not isinstance(returns, tuple):
        returns = [returns]
    assert len(node.returns) == len(
        returns
    ), "Missmatch in Return Length"  # We are dealing with a single output, convert it to a proper port like structure

    shrinked_returns_future = [
        port.cause_shrink(val, structure_registry)
        for port, val in zip(node.returns, returns)
    ]
    try:
        return await asyncio.gather(*shrinked_returns_future)
    except Exception as e:
        raise ShrinkingError(f"Couldn't shrink Returns {returns}") from e
