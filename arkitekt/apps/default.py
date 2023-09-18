from arkitekt.apps.fakts import ArkitektFakts
from arkitekt.apps.herre import ArkitektHerre
from arkitekt.apps.mikro import ArkitektMikro
from arkitekt.apps.fluss import ArkitektFluss
from arkitekt.apps.rekuest import ArkitektRekuest
from arkitekt.apps.unlok import ArkitektUnlok
from koil.composition import Composition
from arkitekt.apps.fakts import build_arkitekt_fakts, build_arkitekt_token_fakts
from arkitekt.apps.herre import build_arkitekt_herre
from arkitekt.apps.rekuest import build_arkitekt_rekuest
from arkitekt.apps.mikro import build_arkitekt_mikro
from arkitekt.apps.unlok import build_arkitekt_unlok
from arkitekt.apps.fluss import build_arkitekt_fluss
from arkitekt.model import Manifest


class App(Composition):
    manifest: Manifest
    fakts: ArkitektFakts
    herre: ArkitektHerre
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


def build_arkitekt_app(
    manifest: Manifest,
    url=None,
    no_cache=False,
    headless=False,
    instance_id=None,
    token=None,
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
    herre = build_arkitekt_herre(
        manifest=manifest, fakts=fakts, url=url, no_cache=no_cache
    )
    rekuest = build_arkitekt_rekuest(fakts=fakts, herre=herre, instance_id=instance_id)
    mikro = build_arkitekt_mikro(fakts=fakts, herre=herre)
    unlok = build_arkitekt_unlok(herre=herre, fakts=fakts)
    fluss = build_arkitekt_fluss(herre=herre, fakts=fakts)

    return App(
        manifest=manifest,
        fakts=fakts,
        herre=herre,
        rekuest=rekuest,
        mikro=mikro,
        unlok=unlok,
        fluss=fluss,
    )
