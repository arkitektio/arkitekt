from arkitekt.apps.fakts import FaktsApp
from herre.grants.fakts import FaktsGrant
from herre.herre import Herre
from pydantic import Field


class ArkitektHerre(Herre):
    grant: FaktsGrant = Field(default_factory=lambda: FaktsGrant())



class HerreApp(FaktsApp):
    herre: ArkitektHerre = Field(default_factory=ArkitektHerre)
    """The fakts layer thats is used for configuration
    """
