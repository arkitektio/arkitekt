from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List

from docstring_parser import compose
from arkitekt.apps.base import BaseApp
from arkitekt.fakts.arkitekt import FaktsArkitekt
from arkitekt.structures.registry import (
    StructureRegistry,
    get_current_structure_registry,
)
from arkitekt.definition.registry import (
    DefinitionRegistry,
    get_current_definition_registry,
)
from arkitekt.arkitekt import Arkitekt
from herre.fakts.herre import FaktsHerre
from rath.links import ShrinkingLink, DictingLink, compose, split, SwitchAsyncLink
from rath.links.shrink import ShrinkingLink
from rath.links.aiohttp import AIOHttpLink
from rath.links.websockets import WebSocketLink
from graphql import OperationType
from arkitekt.agents.stateful import StatefulAgent
from arkitekt.postmans.stateful import StatefulPostman
from arkitekt.agents.transport.websocket import WebsocketAgentTransport
from arkitekt.postmans.transport.websocket import WebsocketPostmanTransport
from rath.links.auth import AuthTokenLink
from test_boil import Fakts


class FaktsApp(BaseApp):
    def __init__(
        self,
        fakts: Fakts = None,
        structure_registry: StructureRegistry = None,
        definition_registry: DefinitionRegistry = None,
    ) -> None:

        fakts = fakts or Fakts()
        herre = FaktsHerre(fakts)
        arkitekt = FaktsArkitekt(herre, fakts)

        agent_transport = WebsocketAgentTransport(
            ws_url=f"ws://{arkitekt_base_url}/agi/",
            instance_id=instance_id,
            token_loader=token_loader,
        )

        agent = StatefulAgent(
            transport=agent_transport,
            definition_registry=definition_registry,
            arkitekt=arkitekt,
        )

        postman_transport = WebsocketPostmanTransport(
            ws_url=f"ws://{arkitekt_base_url}/watchi/",
            instance_id=instance_id,
            token_loader=token_loader,
        )

        postman = StatefulPostman(postman_transport)

        super().__init__(
            arkitekt=arkitekt,
            definition_registry=definition_registry,
            structure_registry=structure_registry,
            agent=agent,
            postman=postman,
        )
