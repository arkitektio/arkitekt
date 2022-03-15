from pydantic import Field
from herre import Herre
from fakts import Fakts
from herre.fakts.herre import FaktsHerre
from koil.composition import Composition
from arkitekt.compositions.base import Arkitekt


class ArkitektApp(Composition):
    fakts: Fakts = Field(default_factory=Fakts)
    herre: Herre = Field(default_factory=FaktsHerre)
    arkitekt: Arkitekt = Field(default_factory=Arkitekt)
