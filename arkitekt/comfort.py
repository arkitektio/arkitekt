from arkitekt.schema import Node
import asyncio

from koil.loop import koil


async def node_to_action(package=None, interface=None, interactive=False) -> Node:
    node = await Node.asyncs.get(package=package, interface=interface)
    return node


def use(package=None, interface=None, interactive=False) -> Node:
    """Use a Node on the Platform by Searching for it on its package

    Args:
        package ([type], optional): The package this Node belongs to. Defaults to None.
        interface ([type], optional):  The interface of this Node. Defaults to None.

    Returns:
        Node: The Node
        
    """
    return koil(node_to_action(package=package, interface=interface))


async def ause(package=None, interface=None, interactive=False) -> Node:
    """Use a Node on the Platform by Searching for it on its package

    Args:
        package ([type], optional): The package this Node belongs to. Defaults to None.
        interface ([type], optional):  The interface of this Node. Defaults to None.

    Returns:
        Node: The Node
        
    """
    return await node_to_action(package=package, interface=interface)
