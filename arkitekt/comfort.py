from arkitekt.graphql.admin import RESET_REPOSITORY
from arkitekt.schema import Node
import asyncio
from herre.wards.registry import get_ward_registry
from koil.loop import koil
import re

package_test = re.compile(r"@(?P<package>[^\/]*)\/(?P<interface>[^\/]*)")


async def ause(q=None, package=None, interface=None) -> Node:
    """Use a Node on the Platform by Searching for it on its package

    Args:
        package ([type], optional): The package this Node belongs to. Defaults to None.
        interface ([type], optional):  The interface of this Node. Defaults to None.

    Returns:
        Node: The Node

    """
    return await Node.asyncs.get(package=package, interface=interface, q=q)


async def areset_repository(**kwargs) -> Node:
    arkitekt_ward = get_ward_registry().get_ward_instance("arkitekt")
    return await arkitekt_ward.arun(RESET_REPOSITORY)


def use(**kwargs) -> Node:
    """Use a Node on the Platform by Searching for it on its package

    Args:
        package ([type], optional): The package this Node belongs to. Defaults to None.
        interface ([type], optional):  The interface of this Node. Defaults to None.

    Returns:
        Node: The Node

    """
    return koil(ause(**kwargs))


def reset_repository(**kwargs) -> Node:
    """Use a Node on the Platform by Searching for it on its package

    Args:
        package ([type], optional): The package this Node belongs to. Defaults to None.
        interface ([type], optional):  The interface of this Node. Defaults to None.

    Returns:
        Node: The Node

    """
    return koil(areset_repository(**kwargs))
