from typing import Any, Awaitable, Callable, Dict, Optional

from pydantic import Field
from arkitekt.agents.transport.websocket import WebsocketAgentTransport
from arkitekt.messages import T
from fakts.fakt.base import Fakt
from fakts.fakts import get_current_fakts
from herre import current_herre


class WebsocketAgentTransportConfig(Fakt):
    endpoint_url: str
    instance_id: str = "default"


class FaktsWebsocketAgentTransport(WebsocketAgentTransport):
    endpoint_url: Optional[str]
    instance_id: Optional[str]
    token_loader: Optional[Callable[[], Awaitable[str]]] = Field(exclude=True)

    fakts_group = "arkitekt.agent"
    _old_fakt: Dict[str, Any] = {}

    def configure(self, fakt: WebsocketAgentTransportConfig) -> None:
        self.endpoint_url = fakt.endpoint_url
        self.instance_id = fakt.instance_id
        self.token_loader = self.token_loader or current_herre.get().aget_token

    async def aconnect(self):
        fakts = get_current_fakts()

        if fakts.has_changed(self._old_fakt, self.fakts_group):
            self._old_fakt = await fakts.aget(self.fakts_group)
            self.configure(WebsocketAgentTransportConfig(**self._old_fakt))

        return await super().aconnect()
