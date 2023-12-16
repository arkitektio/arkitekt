from arkitekt.healthz import FaktsHealthz
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.links.split import SplitLink
from rath.contrib.fakts.links.graphql_ws import FaktsGraphQLWSLink
from rath.contrib.herre.links.auth import HerreAuthLink
from omero_ark.rath import OmeroArkRathLinkComposition, OmeroArkRath
from omero_ark.omero_ark import OmeroArk
from graphql import OperationType

from fakts import Fakts
from herre import Herre


class ArkitektOmeroArk(OmeroArk):
    rath: OmeroArkRath
    healthz: FaktsHealthz


def build_arkitekt_omero_ark(
    fakts: Fakts, herre: Herre, fakts_group: str = "omero_ark"
) -> ArkitektOmeroArk:
    rath = OmeroArkRath(
        link=OmeroArkRathLinkComposition(
            auth=HerreAuthLink(herre=herre),
            split=SplitLink(
                left=FaktsAIOHttpLink(fakts_group=fakts_group, fakts=fakts),
                right=FaktsGraphQLWSLink(fakts_group=fakts_group, fakts=fakts),
                split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
            ),
        )
    )

    return ArkitektOmeroArk(
        rath=rath,
        healthz=FaktsHealthz(fakts_group=fakts_group, fakts=fakts),
    )
