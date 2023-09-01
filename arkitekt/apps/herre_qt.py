from herre.herre import Herre
from fakts.grants.remote import Manifest
from fakts import Fakts
from herre.grants import CacheGrant
from herre.grants.oauth2.refresh import RefreshGrant
from herre.grants.fakts import FaktsGrant
from typing import Optional
from herre.grants.fakts.fakts_login_screen import FaktsQtLoginScreen
from herre.grants.qt.login_screen import LoginWidget


class ArkitektHerreRefreshGrant(RefreshGrant):
    grant: FaktsGrant


class ArkitektHerreChooseFaktsQt(FaktsQtLoginScreen):
    grant: RefreshGrant


class ArkitektHerreQtCacheGrant(CacheGrant):
    grant: ArkitektHerreChooseFaktsQt


class ArkitektHerreQt(Herre):
    grant: ArkitektHerreQtCacheGrant


def build_arkitekt_qt_herre(
    manifest: Manifest,
    fakts: Fakts,
    no_cache: Optional[bool] = False,
    login_widget=None,
    parent=None,
):
    identifier = manifest.identifier
    version = manifest.version

    login_widget = login_widget or LoginWidget(identifier, version, parent=parent)

    return ArkitektHerreQt(
        grant=ArkitektHerreQtCacheGrant(
            cache_file=f".arkitekt/cache/{identifier}-{version}_herre_cache.json",
            hash=f"{identifier}-{version}",
            skip_cache=not no_cache,
            grant=ArkitektHerreChooseFaktsQt(
                fakts=fakts,
                widget=login_widget,
                auto_login=True,
                grant=ArkitektHerreRefreshGrant(
                    grant=FaktsGrant(fakts=fakts, fakts_group="lok")
                ),
            ),
        ),
    )
