from platform import node
from typing import Any
from arkitekt.api.schema import areserve, get_node
from arkitekt.api.schema import (
    afind,
    NodeFragment,
    ReservationFragment,
    areset_repository,
    reset_repository,
)
import asyncio
from arkitekt.messages.postman import unreserve
from koil.loop import koil
import re

package_test = re.compile(r"@(?P<package>[^\/]*)\/(?P<interface>[^\/]*)")


class ReservationContext:
    def __init__(self, res: ReservationFragment) -> None:
        self.res = res

    def aexit(self, exc_type, exc_val, exc_tb):

        unreserve(self.res.id)

    def __aenter__(self):
        pass


class AsyncUsage:
    def __init__(self, node: NodeFragment):
        self.node = node

    def on(self, params) -> "AsyncUsage":
        return self

    async def __aenter__(self) -> ReservationContext:
        self.reserve = await areserve(self.node)
        self.context = ReservationContext(self.reserve)
        await self.context.first_enter()
        return self.context

    async def __aexit__(self, *args, **kwargs) -> None:
        reserve = await unreserve(self.reserve)
        return reserve

    def __call__(self, *args: Any, **kwds: Any) -> Any:

        return self


class SyncUsage:
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        pass


async def ause(**kwargs):
    node = await afind(**kwargs)
    return AsyncUsage(node)
