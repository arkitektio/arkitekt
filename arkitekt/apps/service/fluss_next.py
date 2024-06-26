from fluss_next.fluss import Fluss
from fluss_next.rath import FlussLinkComposition, FlussRath
from rath.links.split import SplitLink
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.contrib.fakts.links.graphql_ws import FaktsGraphQLWSLink
from rath.contrib.herre.links.auth import HerreAuthLink
from graphql import OperationType
from arkitekt.healthz import FaktsHealthz
from fakts import Fakts
from herre import Herre


class ArkitektFluss(Fluss):
    rath: FlussRath
    healthz: FaktsHealthz


def build_arkitekt_fluss(herre: Herre, fakts: Fakts):
    return ArkitektFluss(
        rath=FlussRath(
            link=FlussLinkComposition(
                auth=HerreAuthLink(herre=herre),
                split=SplitLink(
                    left=FaktsAIOHttpLink(fakts_group="fluss", fakts=fakts),
                    right=FaktsGraphQLWSLink(fakts_group="fluss", fakts=fakts),
                    split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
                ),
            )
        ),
        healthz=FaktsHealthz(fakts_group="fluss", fakts=fakts),
    )
