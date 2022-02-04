from rath import compose
from rath.links.context import SwitchAsyncLink
from rath.links.shrink import ShrinkingLink
from rath.fakts.links import FaktsAioHttpLink
from rath.herre.links import HerreAuthTokenLink
from arkitekt.arkitekt import Arkitekt
from herre import Herre, get_current_herre
from fakts import Fakts, get_current_fakts


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

        link = compose(
            ShrinkingLink(),
            SwitchAsyncLink(),
            HerreAuthTokenLink(herre=herre),
            FaktsAioHttpLink(fakts=fakts, fakts_key=fakts_key),
        )

        super().__init__(link, autoconnect)
