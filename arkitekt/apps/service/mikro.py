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


from arkitekt.healthz import FaktsHealthz
from mikro.datalayer import DataLayer
from mikro.mikro import Mikro
from mikro.rath import MikroLinkComposition, MikroRath
from rath.links.split import SplitLink
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.contrib.fakts.links.subscription_transport_ws import FaktsWebsocketLink
from rath.contrib.herre.links.auth import HerreAuthLink
from mikro.contrib.fakts.datalayer import FaktsDataLayer
from mikro.links.datalayer import DataLayerUploadLink
from graphql import OperationType
from fakts import Fakts
from herre import Herre


class ArkitektMikro(Mikro):
    rath: MikroRath
    datalayer: DataLayer
    healthz: FaktsHealthz


def build_arkitekt_mikro(herre: Herre, fakts: Fakts):
    layer = FaktsDataLayer(fakts_group="minio", fakts=fakts, herre=herre)
    return ArkitektMikro(
        rath=MikroRath(
            link=MikroLinkComposition(
                auth=HerreAuthLink(herre=herre),
                split=SplitLink(
                    left=FaktsAIOHttpLink(fakts_group="mikro", fakts=fakts),
                    right=FaktsWebsocketLink(fakts_group="mikro", fakts=fakts),
                    split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
                ),
                datalayer=DataLayerUploadLink(datalayer=layer),
            )
        ),
        datalayer=layer,
        healthz=FaktsHealthz(fakts_group="mikro", fakts=fakts),
    )
