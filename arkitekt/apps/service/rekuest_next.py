from arkitekt.healthz import FaktsHealthz
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.links.split import SplitLink
from rath.contrib.fakts.links.graphql_ws import FaktsGraphQLWSLink
from rath.contrib.herre.links.auth import HerreAuthLink
from rekuest_next.rath import RekuestNextLinkComposition, RekuestNextRath
from rekuest_next.rekuest import RekuestNext
from graphql import OperationType
from rekuest_next.contrib.arkitekt.websocket_agent_transport import (
    ArkitektWebsocketAgentTransport,
)

from rekuest_next.agents.base import BaseAgent
from fakts import Fakts
from herre import Herre
from rekuest_next.postmans.graphql import GraphQLPostman


class ArkitektRekuestNext(RekuestNext):
    rath: RekuestNextRath
    agent: BaseAgent
    healthz: FaktsHealthz


def build_arkitekt_rekuest_next(
    fakts: Fakts, herre: Herre, instance_id: str
) -> ArkitektRekuestNext:
    rath = RekuestNextRath(
        link=RekuestNextLinkComposition(
            auth=HerreAuthLink(herre=herre),
            split=SplitLink(
                left=FaktsAIOHttpLink(fakts_group="rekuest_next", fakts=fakts),
                right=FaktsGraphQLWSLink(fakts_group="rekuest_next", fakts=fakts),
                split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
            ),
        )
    )

    return ArkitektRekuestNext(
        rath=rath,
        agent=BaseAgent(
            transport=ArkitektWebsocketAgentTransport(
                fakts_group="rekuest_next.agent", fakts=fakts, herre=herre
            ),
            instance_id=instance_id,
            rath=rath,
        ),
        postman=GraphQLPostman(
            rath=rath,
            instance_id=instance_id,
        ),
        healthz=FaktsHealthz(fakts_group="rekuest_next", fakts=fakts),
    )
