from graphql import OperationType
from pydantic import Field
from rath import rath
import contextvars
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.contrib.fakts.links.websocket import FaktsWebsocketLink
from rath.contrib.herre.links.auth import HerreAuthLink
from rath.links.aiohttp import AIOHttpLink
from rath.links.auth import AuthTokenLink

from rath.links.base import TerminatingLink
from rath.links.compose import compose
from rath.links.dictinglink import DictingLink
from rath.links.shrink import ShrinkingLink
from rath.links.split import SplitLink
from rath.links.websockets import WebSocketLink

current_arkitekt_rath = contextvars.ContextVar("current_arkitekt_rath", default=None)


class ArkitektRath(rath.Rath):
    link: TerminatingLink = Field(
        default_factory=lambda: compose(
            ShrinkingLink(),
            DictingLink(),
            HerreAuthLink(),
            SplitLink(
                left=FaktsAIOHttpLink(fakts_group="arkitekt"),
                right=FaktsWebsocketLink(fakts_group="arkitekt"),
                split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
            ),
        )
    )

    async def __aenter__(self):
        await super().__aenter__()
        current_arkitekt_rath.set(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await super().__aexit__(exc_type, exc_val, exc_tb)
        current_arkitekt_rath.set(None)
