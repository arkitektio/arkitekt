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


class ArkitektFakts(Fakts):
    pass


def build_arkitekt_fakts(
    manifest: Manifest, url: str = None, no_cache: bool = False, headless: bool = False
) -> ArkitektFakts:
    identifier = manifest.identifier
    version = manifest.version

    return ArkitektFakts(
        grant=CacheGrant(
            cache_file=f".arkitekt/cache/{identifier}-{version}_cache.json",
            hash=f"{identifier}-{version}-{url}",
            skip_cache=no_cache,
            grant=DeviceCodeGrant(
                manifest=manifest,
                open_browser=not headless,
                discovery=WellKnownDiscovery(url=url, auto_protocols=["https", "http"]),
            ),
        )
    )


def build_arkitekt_qt_fakts(
    manifest: Manifest,
    no_cache: Optional[bool] = False,
    beacon_widget=None,
    parent=None,
):
    from fakts.grants.remote.retrieve import RetrieveGrant
    from fakts.discovery.qt.selectable_beacon import (
        SelectBeaconWidget,
        QtSelectableDiscovery,
    )

    identifier = manifest.identifier
    version = manifest.version

    beacon_widget = beacon_widget or SelectBeaconWidget(parent=parent)

    return ArkitektFakts(
        grant=CacheGrant(
            cache_file=f".arkitekt/cache/{identifier}-{version}_fakts_cache.json",
            skip_cache=no_cache,
            grant=RetrieveGrant(
                manifest=manifest,
                redirect_uri="http://localhost:6767",
                discovery=QtSelectableDiscovery(
                    widget=beacon_widget,
                    allow_appending_slash=True,
                    auto_protocols=["http", "https"],
                ),
            ),
        )
    )


def build_arkitekt_token_fakts(
    manifest: Manifest,
    token: str,
    url,
    no_cache: Optional[bool] = False,
    headless=False,
):
    from fakts.grants.remote.static import StaticGrant

    identifier = manifest.identifier
    version = manifest.version

    return ArkitektFakts(
        grant=CacheGrant(
            cache_file=f".arkitekt/cache/{identifier}-{version}_fakts_cache.json",
            skip_cache=no_cache,
            grant=StaticGrant(
                token=token,
                discovery=WellKnownDiscovery(url=url, auto_protocols=["https", "http"]),
            ),
        )
    )
