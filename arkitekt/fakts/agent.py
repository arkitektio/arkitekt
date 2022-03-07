from arkitekt.agents.stateful import StatefulAgent
from arkitekt.agents.transport.websocket import WebsocketAgentTransport
from arkitekt.rath import ArkitektRath
from arkitekt.definition.registry import DefinitionRegistry
from fakts import Fakts, Config
from herre.herre import Herre, current_herre
from arkitekt.rath import ArkitektRath, current_arkitekt_rath


class AgentConfig(Config):
    endpoint_url: str
    instance_id: str

    class Config:
        group = "arkitekt.agent"


class FaktsAgent(StatefulAgent):
    def __init__(
        self,
        fakts: Fakts = None,
        definition_registry: DefinitionRegistry = None,
    ) -> None:

        self.fakts = fakts

        super().__init__(None, definition_registry, None)  #

    def configure(self, config: AgentConfig, herre: Herre, rath: ArkitektRath) -> None:

        self.transport = WebsocketAgentTransport(
            ws_url=config.endpoint_url,
            instance_id=config.instance_id,
            token_loader=herre.aget_token,
        )

        self.rath = rath

    async def __aenter__(self):

        config = await AgentConfig.from_fakts(self.fakts)
        self.configure(
            config, herre=current_herre.get(), rath=current_arkitekt_rath.get()
        )

        return await super().__aenter__()
