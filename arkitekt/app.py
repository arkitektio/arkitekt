from pydantic import Field
from herre import Herre
from fakts import Fakts
from herre.fakts.herre import FaktsHerre
from koil.composition import Composition
from rekuest.compositions.base import Rekuest


class Arkitekt(Composition):
    fakts: Fakts = Field(default_factory=Fakts)
    herre: Herre = Field(default_factory=FaktsHerre)
    rekuest: Rekuest = Field(default_factory=Rekuest)
