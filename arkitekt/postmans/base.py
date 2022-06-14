from typing import Optional

from pydantic import Field

from arkitekt.postmans.transport.base import PostmanTransport
from arkitekt.postmans.transport.fakts import FaktsWebsocketPostmanTransport
from arkitekt.postmans.vars import current_postman
from koil.composition import KoiledModel


class BasePostman(KoiledModel):
    transport: Optional[PostmanTransport] = Field(
        default_factory=FaktsWebsocketPostmanTransport
    )

    """Postman


    Postmans are the the messengers of the arkitekt platform, they are taking care
    of the communication between your app and the arkitekt-server.

    needs to implement:
        broadcast: On assignation Update or on reservation update (non updated fields are none)


    """

    async def __aenter__(self):
        current_postman.set(self)
        self.transport._abroadcast = self.abroadcast
        await self.transport.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.transport.__aexit__(exc_type, exc_val, exc_tb)
        current_postman.set(None)
