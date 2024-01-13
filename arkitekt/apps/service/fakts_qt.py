from fakts.fakts import Fakts
from typing import Optional
from fakts.grants.remote import RemoteGrant
from fakts.grants.remote.demanders.auto_save import AutoSaveDemander
from fakts.grants.remote.discovery.auto_save import AutoSaveDiscovery
from fakts.grants.remote.discovery.qt.auto_save_endpoint_widget import (
    AutoSaveEndpointWidget,
)
from fakts.grants.remote.discovery.qt.qt_settings_endpoint_store import (
    QtSettingsEndpointStore,
)
from fakts.grants.remote.demanders.qt.qt_settings_token_store import QTSettingTokenStore

from fakts.grants.remote.demanders.retrieve import RetrieveDemander
from fakts.grants.remote.claimers.post import ClaimEndpointClaimer
from fakts.grants.remote.discovery.qt.selectable_beacon import (
    SelectBeaconWidget,
    QtSelectableDiscovery,
)
from arkitekt.model import Manifest
from qtpy import QtCore, QtWidgets


class ArkitektFaktsAutoSaveDiscovery(AutoSaveDiscovery):
    """An Arkitekt Fakts discovery that uses Qt widgets for token and endpoint storage"""

    discovery: QtSelectableDiscovery


class ArkitektFaktsQtRemoteGrant(RemoteGrant):
    """An Arkitekt Fakts grant that uses Qt widgets for token and endpoint storage"""

    discovery: ArkitektFaktsAutoSaveDiscovery


class ArkitektFaktsQt(Fakts):
    """A Fakts that uses Qt widgets for token and endpoint storage"""

    grant: ArkitektFaktsQtRemoteGrant


def build_arkitekt_qt_fakts(
    manifest: Manifest,
    no_cache: Optional[bool] = False,
    beacon_widget: Optional[QtWidgets.QWidget] = None,
    parent: Optional[QtWidgets.QWidget] = None,
    settings: Optional[QtCore.QSettings] = None,
) -> ArkitektFaktsQt:
    beacon_widget = beacon_widget or SelectBeaconWidget(
        parent=parent, settings=settings
    )

    return ArkitektFaktsQt(
        grant=RemoteGrant(
            demander=AutoSaveDemander(
                store=QTSettingTokenStore(
                    settings=settings,
                    save_key="fakts_token",
                ),
                demander=RetrieveDemander(
                    manifest=manifest,
                    redirect_uri="http://localhost:6767",
                ),
            ),
            discovery=AutoSaveDiscovery(
                store=QtSettingsEndpointStore(
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
            claimer=ClaimEndpointClaimer(),
        )
    )
