from pydantic import BaseModel, Field
from arkitekt.apps.base import Arkitekt

from fakts.fakts import Fakts
from herre.fakts.herre import FaktsHerre
from herre.herre import Herre


class DefaultApp(BaseModel):
    fakts: Fakts = Field(default_factory=Fakts)
    herre: Herre = Field(default_factory=FaktsHerre)
    arkitekt: Arkitekt = Field(default_factory=Arkitekt)

    async def __aenter__(self):

        await self.fakts.__aenter__()
        await self.herre.__aenter__()
        await self.arkitekt.__aenter__()

    async def __aexit__(self, *args, **kwargs):

        await self.arkitekt.__aexit__(*args, **kwargs)
        await self.herre.__aexit__(*args, **kwargs)
        await self.fakts.__aexit__(*args, **kwargs)
