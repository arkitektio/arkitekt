from arkitekt.healthz import FaktsHealthz
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.links.split import SplitLink
from rath.contrib.fakts.links.subscription_transport_ws import FaktsWebsocketLink
from rath.contrib.herre.links.auth import HerreAuthLink
from reaktion.extension import ReaktionExtension
from rekuest.rath import RekuestLinkComposition, RekuestRath
from rekuest.rekuest import Rekuest
from graphql import OperationType
from rekuest.contrib.arkitekt.websocket_agent_transport import (
    ArkitektWebsocketAgentTransport,
)
from rekuest.agents.base import BaseAgent
from fakts import Fakts
from herre import Herre
from rekuest.postmans.graphql import GraphQLPostman


class ArkitektRekuest(Rekuest):
    rath: RekuestRath
    agent: BaseAgent
    healthz: FaktsHealthz


def build_arkitekt_reaktion_rekuest(
    fakts: Fakts, herre: Herre, instance_id: str
) -> ArkitektRekuest:
    rath = RekuestRath(
        link=RekuestLinkComposition(
            auth=HerreAuthLink(herre=herre),
            split=SplitLink(
                left=FaktsAIOHttpLink(fakts_group="rekuest", fakts=fakts),
                right=FaktsWebsocketLink(fakts_group="rekuest", fakts=fakts),
                split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
            ),
        )
    )

    return ArkitektRekuest(
        rath=rath,
        agent=BaseAgent(
            transport=ArkitektWebsocketAgentTransport(
                fakts_group="rekuest.agent", fakts=fakts, herre=herre
            ),
            extensions={
                "reaktion": ReaktionExtension(),
            },
            instance_id=instance_id,
            rath=rath,
        ),
        postman=GraphQLPostman(
            rath=rath,
            instance_id=instance_id,
        ),
        healthz=FaktsHealthz(fakts_group="rekuest", fakts=fakts),
    )
