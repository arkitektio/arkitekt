from fakts.fakts import Fakts
from koil.composition.base import Composition
from pydantic import Field


class FaktsApp(Composition):
    fakts: Fakts = Field(default_factory=Fakts)
    """The fakts layer that is used for configuration
    """
