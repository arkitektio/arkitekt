from fakts.fakts import Fakts
from koil.composition.base import Composition
from pydantic import Field


class ArkitektFakts(Fakts):
    pass


class FaktsApp(Composition):
    fakts: ArkitektFakts = Field(default_factory=ArkitektFakts)
    """The fakts layer that is used for configuration
    """
