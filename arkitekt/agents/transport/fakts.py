from typing import Awaitable, Callable, Optional

from pydantic import Field
from arkitekt.agents.transport.websocket import WebsocketAgentTransport
from arkitekt.messages import T
from fakts.config.base import Config
from herre import current_herre


class WebsocketAgentTransportConfig(Config):
    endpoint_url: str
    instance_id: str = "default"


class FaktsWebsocketAgentTransport(WebsocketAgentTransport):
    endpoint_url: Optional[str]
    instance_id: Optional[str]
    token_loader: Optional[Callable[[], Awaitable[str]]] = Field(exclude=True)

    async def aconnect(self):
        config = await WebsocketAgentTransportConfig.from_fakts("arkitekt.agent")
        self.endpoint_url = config.endpoint_url
        self.instance_id = config.instance_id
        self.token_loader = self.token_loader or current_herre.get().aget_token
        return await super().aconnect()
