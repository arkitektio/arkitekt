from herre import Herre
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.contrib.fakts.links.graphql_ws import FaktsGraphQLWSLink
from rath.contrib.herre.links.auth import HerreAuthLink
from rath.links.split import SplitLink

from arkitekt.healthz import FaktsHealthz
from fakts import Fakts
from graphql import OperationType
from unlok_next.rath import UnlokLinkComposition, UnlokRath
from unlok_next.unlok import Unlok


class ArkitektUnlok(Unlok):
    rath: UnlokRath
    healthz: FaktsHealthz


def build_arkitekt_unlok_next(herre: Herre, fakts: Fakts):
    return ArkitektUnlok(
        rath=UnlokRath(
            link=UnlokLinkComposition(
                auth=HerreAuthLink(herre=herre),
                split=SplitLink(
                    left=FaktsAIOHttpLink(fakts_group="lok", fakts=fakts),
                    right=FaktsGraphQLWSLink(fakts_group="lok", fakts=fakts),
                    split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
                ),
            )
        ),
        healthz=FaktsHealthz(fakts_group="lok", fakts=fakts),
    )
