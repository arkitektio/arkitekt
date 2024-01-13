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
from kluster.kluster import Kluster
from kluster.rath import KlusterRath, KlusterRathLinkComposition
from rath.links.split import SplitLink
from rath.contrib.fakts.links.aiohttp import FaktsAIOHttpLink
from rath.contrib.fakts.links.graphql_ws import FaktsGraphQLWSLink
from rath.contrib.herre.links.auth import HerreAuthLink
from graphql import OperationType
from herre import Herre
from fakts import Fakts
from kluster.contrib.arkitekt_repository import ArkitektRepository


class ArkitektKluster(Kluster):
    rath: KlusterRath
    repo: ArkitektRepository
    healthz: FaktsHealthz


def build_arkitekt_kluster(herre: Herre, fakts: Fakts):
    repo = ArkitektRepository(
        fakts=fakts,
        herre=herre,
        fakts_key="kluster.gateway_url",
    )

    return ArkitektKluster(
        rath=KlusterRath(
            link=KlusterRathLinkComposition(
                auth=HerreAuthLink(herre=herre),
                split=SplitLink(
                    left=FaktsAIOHttpLink(fakts_group="kluster", fakts=fakts),
                    right=FaktsGraphQLWSLink(fakts_group="kluster", fakts=fakts),
                    split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
                ),
            )
        ),
        healthz=FaktsHealthz(fakts_group="kluster", fakts=fakts),
        repo=repo,
    )
