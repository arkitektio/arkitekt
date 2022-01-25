from arkitekt.api.schema import get_node
from arkitekt.api.schema import (
    aget_node,
    NodeFragment,
    areset_repository,
    reset_repository,
)
import asyncio
from herre.wards.registry import get_ward_registry
from koil.loop import koil
import re

package_test = re.compile(r"@(?P<package>[^\/]*)\/(?P<interface>[^\/]*)")


ause = aget_node
use = get_node
