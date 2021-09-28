from herre.console.context import get_current_console
from typing import Any, Dict, List, Tuple
import asyncio
import logging

logger = logging.getLogger(__name__)

class SerializationError(Exception):
    """Serialization Error

    Serialization Errors are raised when a Shrinking or Expanding Error
    occurs during a shrinking/expanding event
    """
    pass



class ShrinkingError(SerializationError):
    """ Shrinking Error
    
    Is being rased from a Port Shrink Exception
    
    """

class ExpandingError(SerializationError):
    """ Expanding Error
    
    Is being rased from a Port Expand Exception
    
    """





async def shrink_inputs(node, *args, **kwargs) -> Tuple[List[Any], Dict[str, Any]]:
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
    assert len(node.args) == len(args), "Missmatch in Arg Length"
    


    
    shrinked_args_futures = [port.shrink(arg) for port, arg in zip(node.args, args)]

    try:
        shrinked_args = await asyncio.gather(*shrinked_args_futures) # Worrysome because others won't be cancelled on Exception
    except Exception as e:
        raise ShrinkingError(f"Couldn't shrink Arguments {args}") from e

    try:
        shrinked_kwargs = {
            port.key: await port.shrink(kwargs.get(port.key, port.default))
            for port in node.kwargs
        }
    except Exception as e:
        logger.exception(e)
        raise ShrinkingError(f"Couldn't shrink KeywordArguments {kwargs}") from e

    return shrinked_args, shrinked_kwargs
    

async def expand_inputs(node, args: List[Any], kwargs: Dict[str, Any]) -> Tuple[List[Any], Dict[str, Any]]:
    """Expands Args and Kwargs

    Expands the Args and Kwargs according to the Node definition 

    Args:
        node (Node): Nodes
        args (List[Any]): Srhinked Args
        kwargs (Dict[str, Any]): Shrinkag Kwargs

    Raises:
        ExpandingError:  If args are not expandable
        ExpandingError:  If kwargs are not expandable

    Returns:
        Tuple[List[Any], Dict[str, Any]]: Expanded Args, Expanded Kwargs
    """
    assert len(node.args) == len(args), "Missmatch in Arg Length"

    expanded_args_futures = [port.expand(arg) for port, arg in zip(node.args, args)]
    try:
        expanded_args = await asyncio.gather(*expanded_args_futures)
    except Exception as e:
        raise ExpandingError(f"Couldn't expand Args {args}") from e

    try:
        expanded_kwargs = {
            port.key: await port.expand(kwargs.get(port.key, port.default))
            for port in node.kwargs
        }
    except Exception as e:
        raise ExpandingError(f"Couldn't expand Kwargs {kwargs}") from e


    return expanded_args, expanded_kwargs


async def shrink_outputs(node, returns) -> List[Any]:
    """Shrinks returns

    Shrinks the returns according to the Node Definition

    Args:
        node (Node): The Node
        returns (List[any]): The Returns

    Raises:
        ShrinkingError: If returns are not Shrinkable

    Returns:
        List[Any]: Parsed Returns
    """
    if returns is None: returns = []
    if not isinstance(returns, list) and not isinstance(returns, tuple): returns = [returns]
    assert len(node.returns) == len(returns), "Missmatch in Return Length" # We are dealing with a single output, convert it to a proper port like structure
    shrinked_returns_future = [port.shrink(val) for port, val in zip(node.returns, returns)]
    try:
        return await asyncio.gather(*shrinked_returns_future)
    except Exception as e:
        raise ShrinkingError(f"Couldn't shrink Returns {returns}") from e


async def expand_outputs(node, returns) -> List[Any]:
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
    assert len(node.returns) == len(returns), "Missmatch in Return Length"
    
    expanded_returns_future = [port.expand(val) for port, val in zip(node.returns, returns)]
    try:
        returns = await asyncio.gather(*expanded_returns_future)
        if len(returns) == 1: 
            return returns[0] # We are dealing with a single output, just cast back
        else:
            return returns
    except Exception as e:
        logger.exception(e)
        raise ExpandingError(f"Couldn't expand Returns {returns}") from e
