from graphql import OperationType
from rath.links import compose
from rath.links.aiohttp import AIOHttpLink
from rath.links.auth import AuthTokenLink
from rath.links.context import SwitchAsyncLink
from rath.links.dictinglink import DictingLink
from rath.links.shrink import ShrinkingLink
from arkitekt.rath import ArkitektRath
from herre import Herre, current_herre
from fakts import Config
from rath.links.split import SplitLink
from rath.links.websockets import WebSocketLink


class ArkitektRathConfig(Config):
    endpoint_url: str
    ws_endpoint_url: str

    class Config:
        group = "arkitekt"


class FaktsArkitektRath(ArkitektRath):
    def configure(self, config: ArkitektRathConfig, herre: Herre) -> None:
        self.link = compose(
            ShrinkingLink(),
            DictingLink(),  # after the shrinking so we can override the dicting
            SwitchAsyncLink(),
            AuthTokenLink(token_loader=herre.aget_token),
            SplitLink(
                AIOHttpLink(url=config.endpoint_url),
                WebSocketLink(
                    url=config.ws_endpoint_url, token_loader=herre.aget_token
                ),
                lambda o: o.node.operation != OperationType.SUBSCRIPTION,
            ),
        )

    async def __aenter__(self):

        herre = current_herre.get()

        config = await ArkitektRathConfig.from_fakts()
        self.configure(config, herre)

        return await super().__aenter__()
