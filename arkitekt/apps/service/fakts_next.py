from typing import Optional

from fakts.fakts import Fakts
from fakts.grants.remote import RemoteGrant
from fakts.grants.remote.demanders.auto_save import AutoSaveDemander
from fakts.grants.remote.demanders.cache import AutoSaveCacheStore
from fakts.grants.remote.demanders.device_code import DeviceCodeDemander
from fakts.grants.remote.discovery.well_known import WellKnownDiscovery

from arkitekt.model import Manifest


class ArkitektFaktsQt(Fakts):
    grant: RemoteGrant


class ArkitektFaktsNext(Fakts):
    pass


def build_arkitekt_fakts_next(
    manifest: Manifest,
    url: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    client_kind: str = "development",
) -> ArkitektFaktsNext:
    identifier = manifest.identifier
    version = manifest.version

    if no_cache:
        demander = DeviceCodeDemander(
            manifest=manifest,
            redirect_uri="http://localhost:6767",
            open_browser=not headless,
            requested_client_kind=client_kind,
        )

    else:
        demander = AutoSaveDemander(
            demander=DeviceCodeDemander(
                manifest=manifest,
                redirect_uri="http://localhost:6767",
                open_browser=not headless,
                requested_client_kind=client_kind,
            ),
            store=AutoSaveCacheStore(
                cache_file=f".arkitekt/cache/{identifier}-{version}_fakts_cache.json"
            ),
        )

    return ArkitektFaktsNext(
        grant=RemoteGrant(
            demander=demander,
            discovery=WellKnownDiscovery(url=url, auto_protocols=["https", "http"]),
        )
    )
