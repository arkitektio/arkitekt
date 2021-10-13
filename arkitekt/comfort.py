from arkitekt.schema import Node
import asyncio

from koil.loop import koil
import re

package_test = re.compile(r"@(?P<package>[^\/]*)\/(?P<interface>[^\/]*)")

async def node_to_action(**kwargs) -> Node:
    node = await Node.asyncs.get(**kwargs)
    return node


def use(**kwargs) -> Node:
    """Use a Node on the Platform by Searching for it on its package

    Args:
        package ([type], optional): The package this Node belongs to. Defaults to None.
        interface ([type], optional):  The interface of this Node. Defaults to None.

    Returns:
        Node: The Node
        
    """
    return koil(node_to_action(**kwargs))


async def ause(package=None, interface=None, interactive=False) -> Node:
    """Use a Node on the Platform by Searching for it on its package

    Args:
        package ([type], optional): The package this Node belongs to. Defaults to None.
        interface ([type], optional):  The interface of this Node. Defaults to None.

    Returns:
        Node: The Node
        
    """
    return await node_to_action(package=package, interface=interface)
