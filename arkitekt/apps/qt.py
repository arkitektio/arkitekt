from arkitekt.model import Manifest
from arkitekt.apps.types import QtApp
from arkitekt.apps.fallbacks import ImportException, InstallModuleException
from typing import Any, Optional


def build_arkitekt_qt_app(
    manifest: Manifest,
    no_cache: bool = False,
    instance_id: Optional[str] = None,
    beacon_widget: Any = None,
    login_widget: Any = None,
    parent: Any = None,
    settings: Any = None,
):
    if settings is None:
        try:
            from koil.composition.qt import QtPedanticKoil
            from qtpy import QtCore

            settings = QtCore.QSettings()
        except ImportError as e:
            raise InstallModuleException(
                "Please install qtpy to use arkitekt_qt"
            ) from e

    try:
        from arkitekt.apps.service.fakts_qt import build_arkitekt_qt_fakts

        fakts = build_arkitekt_qt_fakts(
            manifest=manifest,
            no_cache=no_cache,
            beacon_widget=beacon_widget,
            parent=parent,
            settings=settings,
        )
    except ImportError as e:
        fakts = ImportException(import_exception=e, install_library="qtpy")

    try:
        from arkitekt.apps.service.herre_qt import build_arkitekt_qt_herre

        herre = build_arkitekt_qt_herre(
            manifest=manifest,
            fakts=fakts,
            login_widget=login_widget,
            parent=parent,
            settings=settings,
        )
    except ImportError as e:
        herre = ImportException(import_exception=e, install_library="qtpy")

    try:
        from arkitekt.apps.service.rekuest import build_arkitekt_rekuest

        rekuest = build_arkitekt_rekuest(
            fakts=fakts, herre=herre, instance_id=instance_id or "main"
        )
    except ImportError as e:
        rekuest = ImportException(import_exception=e, install_library="rekuest")

    try:
        from arkitekt.apps.service.mikro import build_arkitekt_mikro

        mikro = build_arkitekt_mikro(fakts=fakts, herre=herre)
    except ImportError as e:
        mikro = ImportException(import_exception=e, install_library="mikro")

    try:
        from arkitekt.apps.service.unlok import build_arkitekt_unlok

        unlok = build_arkitekt_unlok(herre=herre, fakts=fakts)
    except ImportError as e:
        unlok = ImportException(import_exception=e, install_library="unlok")

    try:
        from arkitekt.apps.service.fluss import build_arkitekt_fluss

        fluss = build_arkitekt_fluss(herre=herre, fakts=fakts)
    except ImportError as e:
        fluss = ImportException(import_exception=e, install_library="fluss")

    try:
        from arkitekt.apps.service.kluster import build_arkitekt_kluster

        kluster = build_arkitekt_kluster(herre=herre, fakts=fakts)
    except ImportError as e:
        kluster = ImportException(import_exception=e, install_library="kluster")

    return QtApp(
        koil=QtPedanticKoil(parent=parent),
        manifest=manifest,
        fakts=fakts,
        herre=herre,
        rekuest=rekuest,
        mikro=mikro,
        unlok=unlok,
        fluss=fluss,
        kluster=kluster,
    )
