from fakts import FaktsGrant
from fakts.fakts import Fakts
from fakts.grants.remote.base import RemoteGrant
from fakts.grants.remote.device_code import DeviceCodeGrant
from koil.composition.base import Composition
from pydantic import Field


class ArkitektFakts(Fakts):
    grant: FaktsGrant = Field(default_factory=DeviceCodeGrant)


class FaktsApp(Composition):
    fakts: ArkitektFakts = Field(default_factory=ArkitektFakts)
    """The fakts layer that is used for configuration
    """
