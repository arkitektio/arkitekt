from arkitekt.apps.fakts_qt import ArkitektFaktsQt, build_arkitekt_qt_fakts
from arkitekt.apps.herre_qt import ArkitektHerreQt, build_arkitekt_qt_herre
from arkitekt.apps.mikro import ArkitektMikro
from arkitekt.apps.rekuest import ArkitektRekuest
from arkitekt.apps.unlok import ArkitektUnlok
from arkitekt.apps.fluss import ArkitektFluss
from koil.composition import Composition
from arkitekt.model import Manifest
from arkitekt.apps.mikro import build_arkitekt_mikro
from arkitekt.apps.unlok import build_arkitekt_unlok
from arkitekt.apps.fluss import build_arkitekt_fluss
from arkitekt.apps.reaktion_rekuest import build_arkitekt_reaktion_rekuest


class QtSchedulingApp(Composition):
    manifest: Manifest
    fakts: ArkitektFaktsQt
    herre: ArkitektHerreQt
    rekuest: ArkitektRekuest
    mikro: ArkitektMikro
    unlok: ArkitektUnlok
    fluss: ArkitektFluss
    """
    Arkitekt

    An app that connected to the services of the arkitekt Api,
    it comes included with the following services:

    - Rekuest: A service for that handles requests to the arkitekt Api as well as provides an
      interface to provide functionality on the arkitekt Api.
    - Herre: A service for that handles the authentication and authorization of the user
    - Fakts: A service for that handles the discovery
      and retrieval of the configuration of the arkitekt Api
    - Mikro: A service for that handles the storage and data of microscopy data

    Apps have to be always used within a context manager, this is to ensure that the services
    are properly closed when the app is no longer needed.

    Example:
        >>> from arkitekt import Arkitekt
        >>> app = Arkitekt()
        >>> with app:
        >>>     # Do stuff
        >>> # App is closed

    """


def build_arkitekt_scheduleqt_app(
    manifest: Manifest,
    no_cache=False,
    instance_id=None,
    beacon_widget=None,
    login_widget=None,
    parent=None,
    settings=None,
):
    fakts = build_arkitekt_qt_fakts(
        manifest=manifest,
        no_cache=no_cache,
        beacon_widget=beacon_widget,
        parent=parent,
        settings=settings,
    )
    herre = build_arkitekt_qt_herre(
        manifest=manifest,
        fakts=fakts,
        login_widget=login_widget,
        parent=parent,
        settings=settings,
    )
    rekuest = build_arkitekt_reaktion_rekuest(
        fakts=fakts, herre=herre, instance_id=instance_id
    )
    mikro = build_arkitekt_mikro(fakts=fakts, herre=herre)
    unlok = build_arkitekt_unlok(herre=herre, fakts=fakts)
    fluss = build_arkitekt_fluss(herre=herre, fakts=fakts)

    return QtSchedulingApp(
        manifest=manifest,
        fakts=fakts,
        herre=herre,
        rekuest=rekuest,
        mikro=mikro,
        unlok=unlok,
        fluss=fluss,
    )
