from fakts.fakts import Fakts
from fakts.fakts import Fakts
from typing import List, Optional
from fakts.grants.remote.discovery.well_known import WellKnownDiscovery
from fakts.grants.remote import RemoteGrant
from fakts.grants.remote.demanders.retrieve import RetrieveDemander
from fakts.grants.remote.demanders.auto_save import AutoSaveDemander
from fakts.grants.remote.demanders.cache import AutoSaveCacheStore
from fakts.grants.remote.demanders.static import StaticDemander
from fakts.grants.remote.demanders.device_code import DeviceCodeDemander
from arkitekt.model import Manifest


class ArkitektFaktsQt(Fakts):
    grant: RemoteGrant


class ArkitektFakts(Fakts):
    pass


def build_arkitekt_fakts(
    manifest: Manifest, url: str = None, no_cache: bool = False, headless: bool = False
) -> ArkitektFakts:
    identifier = manifest.identifier
    version = manifest.version

    if no_cache:
        demander = DeviceCodeDemander(
            manifest=manifest,
            redirect_uri="http://localhost:6767",
            open_browser=not headless,
        )

    else:
        demander = AutoSaveDemander(
            demander=DeviceCodeDemander(
                manifest=manifest,
                redirect_uri="http://localhost:6767",
                open_browser=not headless,
            ),
            store=AutoSaveCacheStore(
                cache_file=f".arkitekt/cache/{identifier}-{version}_fakts_cache.json"
            ),
        )

    return ArkitektFakts(
        grant=RemoteGrant(
            demander=demander,
            discovery=WellKnownDiscovery(url=url, auto_protocols=["https", "http"]),
        )
    )


def build_arkitekt_token_fakts(
    manifest: Manifest,
    token: str,
    url,
    no_cache: Optional[bool] = False,
    headless=False,
):
    return ArkitektFakts(
        grant=RemoteGrant(
            demander=StaticDemander(token=token),
            discovery=WellKnownDiscovery(url=url, auto_protocols=["https", "http"]),
        )
    )
