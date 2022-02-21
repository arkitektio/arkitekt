from typing import Any, Dict, List
from arkitekt.api.schema import NodeFragment
import asyncio
from arkitekt.structures.errors import ExpandingError, ShrinkingError
from arkitekt.structures.registry import StructureRegistry


async def shrink_inputs(
    node: NodeFragment,
    args: List[Any],
    kwargs: Dict[str, Any],
    structure_registry: StructureRegistry,
) -> List[Any]:
    """Shrinks args and kwargs

    Shrinks the inputs according to the Node Definition

    Args:
        node (Node): The Node

    Raises:
        ShrinkingError: If args are not Shrinkable
        ShrinkingError: If kwargs are not Shrinkable

    Returns:
        Tuple[List[Any], Dict[str, Any]]: Parsed Args as a List, Parsed Kwargs as a dict
    """
    if len(node.args) != len(args):
        raise ShrinkingError("Missmatch in Arg Length")

    shrinked_args_futures = [
        port.cause_shrink(arg, structure_registry) for port, arg in zip(node.args, args)
    ]

    try:
        shrinked_args = await asyncio.gather(
            *shrinked_args_futures
        )  # Worrysome because others won't be cancelled on Exception
    except Exception as e:
        raise ShrinkingError(f"Couldn't shrink Arguments {args}") from e

    try:
        shrinked_kwargs = {
            port.key: await port.cause_shrink(
                kwargs.get(port.key, None), structure_registry
            )
            for port in node.kwargs
        }
    except Exception as e:
        raise ShrinkingError(f"Couldn't shrink KeywordArguments {kwargs}") from e

    return shrinked_args, shrinked_kwargs


async def expand_outputs(
    node: NodeFragment,
    returns: List[Any],
    structure_registry: StructureRegistry,
) -> List[Any]:
    """Expands Returns

    Expands the Returns according to the Node definition


    Args:
        node (Node): Node definition
        returns (List[any]): The returns

    Raises:
        ExpandingError: if they are not expandable

    Returns:
        List[Any]: The Expanded Returns
    """
    if len(node.returns) != len(returns):
        raise ExpandingError("Missmatch in Return Length")
    try:
        returns = await asyncio.gather(
            *[
                port.cause_expand(val, structure_registry)
                for port, val in zip(node.returns, returns)
            ]
        )

        if len(returns) == 1:
            return returns[0]  # We are dealing with a single output, just cast back
        else:
            return returns
    except Exception as e:
        raise ExpandingError(f"Couldn't expand Returns {returns}") from e
