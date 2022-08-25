from arkitekt.apps.fakts import FaktsApp
from fakts.fakts import Fakts
from herre.fakts.herre import FaktsHerre
from herre.herre import Herre
from koil.composition.base import Composition
from pydantic import Field


class HerreApp(FaktsApp):
    herre: Herre = Field(default_factory=FaktsHerre)
    """The fakts layer that is used for configuration
    """
