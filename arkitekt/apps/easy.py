from arkitekt.model import Manifest
from .types import EasyApp
from arkitekt.apps.fallbacks import ImportException
from arkitekt.apps.service.fakts import build_arkitekt_fakts, build_arkitekt_token_fakts
from arkitekt.apps.service.herre import build_arkitekt_herre
from typing import Optional, List


def build_arkitekt_easy_app(
    manifest: Manifest,
    url: Optional[str] = None,
    no_cache: bool = False,
    headless: bool = False,
    instance_id: Optional[str] = None,
    token: Optional[str] = None,
    enforce: Optional[List[str]] = None,
):
    fakts = (
        build_arkitekt_fakts(
            manifest=manifest, url=url, no_cache=no_cache, headless=headless
        )
        if not token
        else build_arkitekt_token_fakts(
            manifest=manifest,
            token=token,
            url=url,
            no_cache=no_cache,
            headless=headless,
        )
    )
    herre = build_arkitekt_herre(fakts=fakts)

    try:
        from arkitekt.apps.service.rekuest import build_arkitekt_rekuest

        rekuest = build_arkitekt_rekuest(
            fakts=fakts, herre=herre, instance_id=instance_id or "main"
        )
    except ImportError as e:
        if enforce and "rekuest" in enforce:
            raise e
        rekuest = ImportException(import_exception=e, install_library="rekuest")

    try:
        from arkitekt.apps.service.mikro import build_arkitekt_mikro

        mikro = build_arkitekt_mikro(fakts=fakts, herre=herre)
    except ImportError as e:
        if enforce and "mikro" in enforce:
            raise e
        mikro = ImportException(import_exception=e, install_library="mikro")

    try:
        from arkitekt.apps.service.unlok import build_arkitekt_unlok

        unlok = build_arkitekt_unlok(herre=herre, fakts=fakts)
    except ImportError as e:
        if enforce and "unlok" in enforce:
            raise e
        unlok = ImportException(import_exception=e, install_library="unlok")

    try:
        from arkitekt.apps.service.fluss import build_arkitekt_fluss

        fluss = build_arkitekt_fluss(herre=herre, fakts=fakts)
    except ImportError as e:
        if enforce and "fluss" in enforce:
            raise e
        fluss = ImportException(import_exception=e, install_library="fluss")

    try:
        from arkitekt.apps.service.omero_ark import build_arkitekt_omero_ark

        omero_ark = build_arkitekt_omero_ark(herre=herre, fakts=fakts)
    except ImportError as e:
        if enforce and "omero_ark" in enforce:
            raise e
        omero_ark = ImportException(import_exception=e, install_library="omero_ark")

    try:
        from arkitekt.apps.service.kluster import build_arkitekt_kluster

        kluster = build_arkitekt_kluster(herre=herre, fakts=fakts)
    except ImportError as e:
        if enforce and "kluster" in enforce:
            raise e
        kluster = ImportException(import_exception=e, install_library="kluster")

    return EasyApp(
        manifest=manifest,
        fakts=fakts,
        herre=herre,
        rekuest=rekuest,
        mikro=mikro,
        unlok=unlok,
        fluss=fluss,
        omero_ark=omero_ark,
        kluster=kluster,
    )
