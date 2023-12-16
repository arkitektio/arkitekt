from unlok import Unlok
from unlok.rath import UnlokRath, UnlokLinkComposition
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.contrib.herre.links.auth import HerreAuthLink
from herre import Herre
from fakts import Fakts


class ArkitektUnlok(Unlok):
    rath: UnlokRath


def build_arkitekt_unlok(herre: Herre, fakts: Fakts):
    return ArkitektUnlok(
        rath=UnlokRath(
            link=UnlokLinkComposition(
                auth=HerreAuthLink(herre=herre),
                split=FaktsAIOHttpLink(fakts_group="lok", fakts=fakts),
            )
        )
    )
