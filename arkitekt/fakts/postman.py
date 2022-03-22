from typing import Optional
from arkitekt.postmans.stateful import StatefulPostman
from arkitekt.postmans.transport.websocket import WebsocketPostmanTransport
from fakts.config.base import Config
from fakts.fakts import Fakts, current_fakts
from herre.herre import Herre, current_herre


class PostmanConfig(Config):
    endpoint_url: str
    instance_id: str

    class Config:
        group = "arkitekt.postman"


class FaktsPostman(StatefulPostman):
    herre: Optional[Herre] = None
    fakts: Optional[Fakts] = None

    def configure(
        self,
        config: PostmanConfig,
        herre: Herre,
    ) -> None:
        self.transport = WebsocketPostmanTransport(
            ws_url=config.endpoint_url,
            instance_id=config.instance_id,
            token_loader=herre.aget_token,
        )

    async def __aenter__(self):

        herre = self.herre or current_herre.get()
        fakts = self.fakts or current_fakts.get()

        config = await PostmanConfig.from_fakts(fakts=fakts)
        self.configure(config, herre)

        return await super().__aenter__()
