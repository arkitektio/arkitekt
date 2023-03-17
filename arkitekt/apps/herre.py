from arkitekt.apps.fakts import FaktsApp
from herre.herre import Herre
from pydantic import Field


class ArkitektHerre(Herre):
    pass



class HerreApp(FaktsApp):
    herre: ArkitektHerre = Field(default_factory=ArkitektHerre)
    """The fakts layer thats is used for configuration
    """
