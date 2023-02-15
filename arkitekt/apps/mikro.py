"""
This modules provides the main app. It is responsible for setting up the connection to the mikro-server and
handling authentification and setting up the configuration. Mikro handles the creation of the datalayer and
the graphql client.

You can compose this app together with other apps to create a full fledged app. (Like combining with
arkitekt to enable to call functions that you define on the app)

Example:

    A simple app that takes it configuraiton from basic.fakts and connects to the mikro-server.
    You can define all of the logic within the context manager

    ```python
    from mikro.app import MikroApp

    app = MikroApp(fakts=Fakts(subapp="basic"))

    with app:
        # do stuff

    ```

    Async Usage:


    ```python
    from mikro.app import MikroApp

    app = MikroApp(fakts=Fakts(subapp="basic"))

    async with app:
        # do stuff

    ```

 
"""


from arkitekt.apps.herre import HerreApp
from pydantic import Field
from arkitekt.healthz import FaktsHealthz
from mikro.datalayer import DataLayer
from mikro.mikro import Mikro
from mikro.rath import MikroLinkComposition, MikroRath
from rath.links.split import SplitLink
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.contrib.fakts.links.websocket import FaktsWebsocketLink
from rath.contrib.herre.links.auth import HerreAuthLink
from mikro.contrib.fakts.datalayer import FaktsDataLayer
from graphql import OperationType


class ArkitektMikro(Mikro):
    rath: MikroRath = Field(
        default_factory=lambda: MikroRath(
            link=MikroLinkComposition(
                auth=HerreAuthLink(),
                split=SplitLink(
                    left=FaktsAIOHttpLink(fakts_group="mikro"),
                    right=FaktsWebsocketLink(fakts_group="mikro"),
                    split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
                ),
            )
        )
    )
    datalayer: DataLayer = Field(
        default_factory=lambda: FaktsDataLayer(fakts_group="minio")
    )
    healthz: FaktsHealthz = Field(
        default_factory=lambda: FaktsHealthz(fakts_group="mikro")
    )


class MikroApp(HerreApp):
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

    mikro: ArkitektMikro = Field(default_factory=ArkitektMikro)
