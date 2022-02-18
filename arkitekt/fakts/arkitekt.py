from graphql import OperationType
from rath import compose
from rath.links.context import SwitchAsyncLink
from rath.links.dictinglink import DictingLink
from rath.links.shrink import ShrinkingLink
from rath.fakts.links import FaktsAioHttpLink
from rath.herre.links import HerreAuthTokenLink
from arkitekt.arkitekt import Arkitekt
from herre import Herre, get_current_herre
from fakts import Fakts, get_current_fakts
from rath.links.split import SplitLink
from rath.links.websockets import WebSocketLink


class FaktsArkitekt(Arkitekt):
    def __init__(
        self,
        herre: Herre = None,
        fakts: Fakts = None,
        fakts_key: str = "arkitekt",
        autoconnect=True,
    ) -> None:

        herre = herre or get_current_herre()
        fakts = fakts or get_current_fakts()
        fakts.assert_groups.add("arkitekt")

        link = compose(
            ShrinkingLink(),
            DictingLink(),  # after the shrinking so we can override the dicting
            SwitchAsyncLink(),
            HerreAuthTokenLink(herre=herre),
            SplitLink(
                FaktsAioHttpLink(fakts=fakts, fakts_key="arkitekt"),
                WebSocketLink(
                    url="ws://localhost:8090/graphql", token_loader=herre.aget_token
                ),
                lambda o: o.node.operation != OperationType.SUBSCRIPTION,
            ),
        )

        super().__init__(link, autoconnect)
