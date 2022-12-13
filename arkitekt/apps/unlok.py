from .herre import HerreApp
from unlok import Unlok
from unlok.rath import UnlokRath, UnlokLinkComposition
from pydantic import Field
from rath.links.split import SplitLink
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.contrib.fakts.links.websocket import FaktsWebsocketLink
from rath.contrib.herre.links.auth import HerreAuthLink
from mikro.contrib.fakts.datalayer import FaktsDataLayer
from graphql import OperationType


class ArkitektUnlok(Unlok):
    rath: UnlokRath = Field(
        default_factory=lambda: UnlokRath(
            link=UnlokLinkComposition(
                auth=HerreAuthLink(),
                split=SplitLink(
                    left=FaktsAIOHttpLink(fakts_group="herre"),
                    right=FaktsWebsocketLink(fakts_group="herre"),
                    split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
                ),
            )
        )
    )


class UnlokApp(HerreApp):
    """Lok App"""

    lok: ArkitektUnlok = Field(default_factory=ArkitektUnlok)
