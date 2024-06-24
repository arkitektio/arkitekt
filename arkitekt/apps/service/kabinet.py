from kabinet.kabinet import Kabinet
from kabinet.rath import KabinetLinkComposition, KabinetRath
from rath.links.split import SplitLink
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.contrib.fakts.links.graphql_ws import FaktsGraphQLWSLink
from rath.contrib.herre.links.auth import HerreAuthLink
from graphql import OperationType
from arkitekt.healthz import FaktsHealthz
from fakts import Fakts
from herre import Herre


class ArkitektKabinet(Kabinet):
    rath: KabinetRath
    healthz: FaktsHealthz


def build_arkitekt_kabinet(herre: Herre, fakts: Fakts):
    return ArkitektKabinet(
        rath=KabinetRath(
            link=KabinetLinkComposition(
                auth=HerreAuthLink(herre=herre),
                split=SplitLink(
                    left=FaktsAIOHttpLink(fakts_group="kabinet", fakts=fakts),
                    right=FaktsGraphQLWSLink(fakts_group="kabinet", fakts=fakts),
                    split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
                ),
            )
        ),
        healthz=FaktsHealthz(fakts_group="kabinet", fakts=fakts),
    )
