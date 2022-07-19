from typing import Any, Dict, List
from arkitekt.api.schema import NodeFragment
import asyncio
from arkitekt.structures.errors import ExpandingError, ShrinkingError
from arkitekt.structures.registry import StructureRegistry
from arkitekt.structures.serialization.utils import aexpand, ashrink


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
    try:
        if len(node.args) > len(args) + len(kwargs):
            raise ShrinkingError(f"More parameters needed {node.args} vs {args}")
    except TypeError as e:
        raise ShrinkingError() from e

    shrinked_args_futures = []

    args_iterator = iter(args)

    try:
        try:
            for port in node.args:
                if port.key in kwargs:
                    shrinked_args_futures.append(
                        asyncio.create_task(
                            ashrink(
                                port, kwargs.get(port.key, None), structure_registry
                            )
                        )
                    )
                else:
                    shrinked_args_futures.append(
                        asyncio.create_task(
                            ashrink(port, next(args_iterator), structure_registry)
                        )
                    )
        except StopIteration:
            raise ShrinkingError(f"More parameters needed {node.args} vs {args}")

        shrinked_args = await asyncio.gather(
            *shrinked_args_futures
        )  # Worrysome because others won't be cancelled on Exception
    except Exception as e:

        for future in shrinked_args_futures:
            future.cancel()

        await asyncio.gather(*shrinked_args_futures, return_exceptions=True)

        raise ShrinkingError(
            f"Couldn't shrink Arguments {args} with {node.args}"
        ) from e

    try:
        shrinked_kwargs = {
            port.key: await ashrink(
                port, kwargs.get(port.key, None), structure_registry
            )
            for port in node.kwargs
        }
    except Exception as e:
        raise ShrinkingError(
            f"Couldn't shrink KeywordArguments {kwargs} with {node.kwargs}"
        ) from e

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
    assert returns is not None, "Returns can't be empty"
    if len(node.returns) != len(returns):
        raise ExpandingError(
            f"Missmatch in Return Length. Node requires {len(node.returns)} returns, but got {len(returns)}"
        )
    try:
        if len(returns) == 0:
            return None

        returns = await asyncio.gather(
            *[
                aexpand(port, val, structure_registry)
                for port, val in zip(node.returns, returns)
            ]
        )

        if len(returns) == 1:
            return returns[0]  # We are dealing with a single output, just cast back
        else:
            return returns
    except Exception as e:
        raise ExpandingError(f"Couldn't expand Returns {returns}") from e
