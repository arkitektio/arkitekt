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
from mikro_next.mikro_next import MikroNext
from mikro_next.rath import MikroNextLinkComposition, MikroNextRath
from rath.links.split import SplitLink
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.contrib.fakts.links.graphql_ws import FaktsGraphQLWSLink
from rath.contrib.herre.links.auth import HerreAuthLink
from mikro_next.contrib.fakts.datalayer import FaktsDataLayer
from mikro_next.links.upload import UploadLink
from mikro_next.datalayer import DataLayer
from graphql import OperationType
from herre import Herre
from fakts import Fakts


class ArkitektMikroNext(MikroNext):
    rath: MikroNextRath
    datalayer: DataLayer
    healthz: FaktsHealthz


def build_arkitekt_mikro_next(herre: Herre, fakts: Fakts):
    datalayer = FaktsDataLayer(fakts_group="minio", fakts=fakts)

    return ArkitektMikroNext(
        rath=MikroNextRath(
            link=MikroNextLinkComposition(
                auth=HerreAuthLink(herre=herre),
                upload=UploadLink(
                    datalayer=datalayer,
                ),
                split=SplitLink(
                    left=FaktsAIOHttpLink(fakts_group="mikro_new", fakts=fakts),
                    right=FaktsGraphQLWSLink(fakts_group="mikro_new", fakts=fakts),
                    split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
                ),
            )
        ),
        datalayer=datalayer,
        healthz=FaktsHealthz(fakts_group="mikro", fakts=fakts),
    )
