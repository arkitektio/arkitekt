from arkitekt.apps.herre import HerreApp
from pydantic import Field
from fluss.fluss import Fluss
from fluss.rath import FlussLinkComposition, FlussRath
from rath.links.split import SplitLink
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.contrib.fakts.links.websocket import FaktsWebsocketLink
from rath.contrib.herre.links.auth import HerreAuthLink
from graphql import OperationType
from .rekuest import RekuestApp
from .unlok import UnlokApp
from arkitekt.healthz import FaktsHealthz


class ArkitektFluss(Fluss):
    rath: FlussRath = Field(
        default_factory=lambda: FlussRath(
            link=FlussLinkComposition(
                auth=HerreAuthLink(),
                split=SplitLink(
                    left=FaktsAIOHttpLink(fakts_group="fluss"),
                    right=FaktsWebsocketLink(fakts_group="fluss"),
                    split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
                ),
            )
        )
    )
    healthz: FaktsHealthz = Field(
        default_factory=lambda: FaktsHealthz(fakts_group="fluss")
    )


class FlussApp(HerreApp):
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

    fluss: ArkitektFluss = Field(default_factory=ArkitektFluss)


class ConnectedFluss(RekuestApp, UnlokApp, FlussApp):
    pass
