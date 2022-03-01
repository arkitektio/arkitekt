from arkitekt.agents.stateful import StatefulAgent
from arkitekt.agents.transport.websocket import WebsocketAgentTransport
from arkitekt.definition.registry import DefinitionRegistry
from fakts import Fakts
from test_boil import Arkitekt


class FaktsAgent(StatefulAgent):
    def __init__(
        self,
        fakts: Fakts,
        arkitekt: Arkitekt,
        definition_registry: DefinitionRegistry = None,
    ) -> None:
        super().__init__(None, definition_registry, arkitekt)
        self._fakts = fakts

    async def __aenter__(self):
        config = self._fakts.aget("arkitekt.agent")

        transport = WebsocketAgentTransport(config)

        return await super().__aenter__()
