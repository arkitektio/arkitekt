from typing import Any
from arkitekt.traits.node import Reserve
from arkitekt.api.schema import ArgPortFragment, KwargPortFragment, NodeType, PortType
from arkitekt.postmans.utils import use


def assign(node: Reserve, *args, **kwargs) -> Any:
    """Assign a task to a Node

    Args:
        node (Reserve): Node to assign to
        args (tuple): Arguments to pass to the node
        kwargs (dict): Keyword arguments to pass to the node
    Returns:
        Any: Result of the node task

    """
    assert node.get_node_type() == NodeType.FUNCTION
    with use(x, auto_unreserve=False) as r:
        x = node.assign(*args, **kwargs)
        print(x)
