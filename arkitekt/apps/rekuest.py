from arkitekt.apps.herre import HerreApp
from pydantic import Field
from arkitekt.healthz import FaktsHealthz
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.links.split import SplitLink
from rath.contrib.fakts.links.websocket import FaktsWebsocketLink
from rath.contrib.herre.links.auth import HerreAuthLink
from rekuest.rath import RekuestLinkComposition, RekuestRath
from rekuest.rekuest import Rekuest
from graphql import OperationType
from rekuest.contrib.fakts.websocket_agent_transport import FaktsWebsocketAgentTransport
from rekuest.agents.stateful import StatefulAgent


class ArkitektAgent(StatefulAgent):
    transport: FaktsWebsocketAgentTransport = Field(
        default_factory=lambda: FaktsWebsocketAgentTransport(fakts_group="rekuest.agent")
    )

class ArkitektRekuest(Rekuest):
    rath: RekuestRath = Field(
        default_factory=lambda: RekuestRath(
            link=RekuestLinkComposition(
                auth=HerreAuthLink(),
                split=SplitLink(
                    left=FaktsAIOHttpLink(fakts_group="rekuest"),
                    right=FaktsWebsocketLink(fakts_group="rekuest"),
                    split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
                ),
            )
        )
    )
    agent: StatefulAgent = Field(
        default_factory=lambda: ArkitektAgent()
    )
    healthz: FaktsHealthz = Field(
        default_factory=lambda: FaktsHealthz(fakts_group="rekuest")
    )


class RekuestApp(HerreApp):
    """Mikro App

    It is responsible for setting up the connection to the mikro-server and
    handling authentification and setting up the configuration. Mikro handles the creation of the datalayer and
    the graphql client.

    You can compose this app together with other apps to create a full fledged app. (Like combining with
    arkitekt to enable to call functions that you define on the app). See the example in the docstring.

    Attributes:
        fakts (Fakts): The fakts instance to use.
        mikro (Mikro): The mikro instance to use.
        herre (Herre): The herre instance to use.

    """

    rekuest: ArkitektRekuest = Field(default_factory=ArkitektRekuest)
    """The mikro layer that is used for the datalayer and
    api client
    """
