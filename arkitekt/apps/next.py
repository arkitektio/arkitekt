from arkitekt.model import Manifest
from .types import NextApp
from arkitekt.apps.fallbacks import ImportException
from arkitekt.apps.service.fakts_next import build_arkitekt_fakts_next
from arkitekt.apps.service.herre import build_arkitekt_herre


def build_next_app(
    manifest: Manifest,
    url=None,
    no_cache=False,
    headless=False,
    instance_id=None,
    token=None,
    app_kind="development",
):
    fakts = build_arkitekt_fakts_next(
        manifest=manifest,
        url=url,
        no_cache=no_cache,
        headless=headless,
        client_kind=app_kind,
    )

    herre = build_arkitekt_herre(fakts=fakts)

    try:
        from arkitekt.apps.service.rekuest_next import build_arkitekt_rekuest_next

        rekuest = build_arkitekt_rekuest_next(
            fakts=fakts, herre=herre, instance_id=instance_id
        )
    except ImportError as e:
        rekuest = ImportException(import_exception=e, install_library="rekuest_next")

    try:
        from arkitekt.apps.mikro_next import build_arkitekt_mikro_next

        mikro = build_arkitekt_mikro_next(fakts=fakts, herre=herre)
    except ImportError as e:
        mikro = ImportException(import_exception=e, install_library="mikro_next")

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
        from arkitekt.apps.service.omero_ark import build_arkitekt_omero_ark

        omero_ark = build_arkitekt_omero_ark(herre=herre, fakts=fakts)
    except ImportError as e:
        omero_ark = ImportException(import_exception=e, install_library="omero_ark")

    try:
        from arkitekt.apps.service.kluster import build_arkitekt_kluster

        kluster = build_arkitekt_kluster(herre=herre, fakts=fakts)
    except ImportError as e:
        kluster = ImportException(import_exception=e, install_library="kluster")

    return NextApp(
        manifest=manifest,
        fakts=fakts,
        herre=herre,
        rekuest=rekuest,
        mikro=mikro,
        unlok=unlok,
        fluss=fluss,
        kluster=kluster,
        omero_ark=omero_ark,
    )
