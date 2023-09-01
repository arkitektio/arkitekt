from fakts.fakts import Fakts
from koil.composition.base import Composition
from pydantic import Field
from fakts.fakts import Fakts
from fakts.grants.remote.static import StaticGrant
from fakts.grants import CacheGrant
from herre.grants import CacheGrant as HerreCacheGrant
from herre.grants.oauth2.refresh import RefreshGrant
from herre.grants.fakts import FaktsGrant
from fakts.grants.remote import Manifest
from typing import List, Optional
from fakts.discovery.well_known import WellKnownDiscovery
from fakts.grants.remote.device_code import DeviceCodeGrant
from fakts.grants.remote import Manifest
from fakts.grants.remote.retrieve import RetrieveGrant
from fakts.discovery.qt.selectable_beacon import (
    SelectBeaconWidget,
    QtSelectableDiscovery,
)


class ArkitektFaktsRetrieveGrant(RetrieveGrant):
    discovery: QtSelectableDiscovery


class ArkitektFaktsQtCacheGrant(CacheGrant):
    grant: ArkitektFaktsRetrieveGrant


class ArkitektFaktsQt(Fakts):
    grant: ArkitektFaktsQtCacheGrant
    pass


def build_arkitekt_qt_fakts(
    manifest: Manifest,
    no_cache: Optional[bool] = False,
    beacon_widget=None,
    parent=None,
):
    identifier = manifest.identifier
    version = manifest.version

    beacon_widget = beacon_widget or SelectBeaconWidget(parent=parent)

    return ArkitektFaktsQt(
        grant=CacheGrant(
            cache_file=f".arkitekt/cache/{identifier}-{version}_fakts_cache.json",  # no url
            skip_cache=True,
            grant=RetrieveGrant(
                manifest=manifest,
                redirect_uri="http://localhost:6767",
                discovery=QtSelectableDiscovery(
                    widget=beacon_widget,
                    allow_appending_slash=True,
                    auto_protocols=["http", "https"],
                ),
            ),
        ),
        assert_groups={"mikro", "rekuest"},
    )
