from herre.herre import Herre
from fakts.grants.remote import Manifest
from fakts import Fakts
from herre.grants import CacheGrant as HerreCacheGrant
from herre.grants.oauth2.refresh import RefreshGrant
from herre.grants.fakts import FaktsGrant
from typing import Optional


class ArkitektHerre(Herre):
    pass


def build_arkitekt_herre(
    manifest: Manifest, fakts: Fakts, url: str, no_cache: Optional[bool] = False
) -> ArkitektHerre:
    identifier = manifest.identifier
    version = manifest.version

    return ArkitektHerre(
        grant=HerreCacheGrant(
            cache_file=f".arkitekt/cache/{identifier}-{version}_herre_cache.json",
            hash=f"{identifier}-{version}-{url}",
            skip_cache=no_cache,
            grant=RefreshGrant(grant=FaktsGrant(fakts=fakts, fakts_group="lok")),
        ),
    )


def build_arkitekt_qt_herre(
    manifest: Manifest,
    fakts: Fakts,
    url: str,
    no_cache: Optional[bool] = False,
    login_widget=None,
    parent=None,
):
    from herre.grants.fakts.fakts_login_screen import FaktsQtLoginScreen
    from herre.grants.qt.login_screen import LoginWidget

    identifier = manifest.identifier
    version = manifest.version

    login_widget = login_widget or LoginWidget(identifier, version, parent=parent)

    return ArkitektHerre(
        grant=HerreCacheGrant(
            cache_file=f".arkitekt/cache/{identifier}-{version}_herre_cache.json",
            hash=f"{identifier}-{version}",
            skip_cache=True,
            grant=FaktsQtLoginScreen(
                fakts=fakts,
                widget=login_widget,
                auto_login=True,
                grant=RefreshGrant(grant=FaktsGrant(fakts=fakts, fakts_group="lok")),
            ),
        ),
    )
