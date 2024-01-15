from herre.herre import Herre
from fakts import Fakts
from herre.grants.oauth2.refresh import RefreshGrant
from herre.fakts.grant import FaktsGrant
from herre.fakts.fakts_qt_store import FaktsQtStore

from herre.grants.auto_login import AutoLoginGrant
from herre.grants.qt.auto_login import AutoLoginWidget
from herre.fakts.fakts_endpoint_fetcher import FaktsUserFetcher
from arkitekt.model import Manifest, User
from arkitekt.apps.service.grant_registry import ARKITEKT_GRANT_REGISTRY


class ArkitektAutoLogin(AutoLoginGrant):
    store: FaktsQtStore
    fetcher: FaktsUserFetcher
    grant: FaktsGrant


class ArkitektRefreshGrant(RefreshGrant):
    grant: ArkitektAutoLogin


class ArkitektHerreQt(Herre):
    grant: ArkitektRefreshGrant


def build_arkitekt_qt_herre(
    manifest: Manifest,
    fakts: Fakts,
    login_widget=None,
    parent=None,
    settings=None,
):
    login_widget = login_widget or AutoLoginWidget(parent=parent)

    grant = ArkitektAutoLogin(
        store=FaktsQtStore(
            fakts=fakts,
            settings=settings,
            fakts_key="lok.endpoint_url",
        ),
        widget=login_widget,
        fetcher=FaktsUserFetcher(
            fakts=fakts, fakts_key="lok.userinfo_url", userModel=User
        ),
        grant=FaktsGrant(
            fakts=fakts, fakts_group="lok", grant_registry=ARKITEKT_GRANT_REGISTRY
        ),
    )

    return ArkitektHerreQt(
        grant=ArkitektRefreshGrant(grant=grant),
        fetcher=FaktsUserFetcher(
            fakts=fakts, fakts_key="lok.userinfo_url", userModel=User
        ),
    )
