from fakts.fakts import Fakts
from typing import Optional
from fakts.grants.remote import RemoteGrant
from fakts.grants.remote.demanders.auto_save import AutoSaveDemander
from fakts.grants.remote.discovery.auto_save import AutoSaveDiscovery
from fakts.grants.remote.discovery.qt.auto_save_store import AutoSaveEndpointStore
from fakts.grants.remote.discovery.qt.auto_save_widget import AutoSaveEndpointWidget
from fakts.grants.remote.demanders.qt.auto_save_store import AutoSaveTokenStore
from fakts.grants.remote.demanders.qt.auto_save_widget import AutoSaveTokenWidget

from fakts.grants.remote.demanders.retrieve import RetrieveDemander
from fakts.grants.remote.discovery.qt.selectable_beacon import (
    SelectBeaconWidget,
    QtSelectableDiscovery,
)
from arkitekt.model import Manifest


class ArkitektFaktsQtRemoteGrant(RemoteGrant):
    discovery: AutoSaveDiscovery


class ArkitektFaktsQt(Fakts):
    grant: ArkitektFaktsQtRemoteGrant


def build_arkitekt_qt_fakts(
    manifest: Manifest,
    no_cache: Optional[bool] = False,
    beacon_widget=None,
    parent=None,
    settings=None,
):
    beacon_widget = beacon_widget or SelectBeaconWidget(
        parent=parent, settings=settings
    )

    return ArkitektFaktsQt(
        grant=RemoteGrant(
            demander=AutoSaveDemander(
                store=AutoSaveTokenStore(
                    settings=settings,
                    save_key="fakts_token",
                ),
                demander=RetrieveDemander(
                    manifest=manifest,
                    redirect_uri="http://localhost:6767",
                ),
            ),
            discovery=AutoSaveDiscovery(
                store=AutoSaveEndpointStore(
                    settings=settings,
                    save_key="fakts_endpoint",
                ),
                decider=AutoSaveEndpointWidget(
                    parent=parent,
                ),
                discovery=QtSelectableDiscovery(
                    widget=beacon_widget,
                    settings=settings,
                    allow_appending_slash=True,
                    auto_protocols=["http", "https"],
                ),
            ),
        )
    )
