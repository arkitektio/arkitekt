from arkitekt.apps.fakts import FaktsApp
from herre.fakts.herre import FaktsHerre
from herre.herre import Herre
from pydantic import Field


class HerreApp(FaktsApp):
    herre: Herre = Field(default_factory=FaktsHerre)
    """The fakts layer that is used for configuration
    """
