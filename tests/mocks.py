from pydantic import Field
from arkitekt.agents.base import BaseAgent
from arkitekt.agents.stateful import StatefulAgent
from arkitekt.agents.transport.mock import MockAgentTransport
from arkitekt.api.schema import (
    NodeType,
    PortType,
    ProvisionStatus,
)
from rath.links.base import TerminatingLink
from rath.links.testing.mock import AsyncMockResolver, AsyncMockLink
from rath.links.testing.statefulmock import AsyncMockResolver
from rath.links import compose
from rath.links.dictinglink import DictingLink
from rath.links.shrink import ShrinkingLink
from rath.operation import Operation
from arkitekt.rath import ArkitektRath

from arkitekt.postmans.transport.mock import MockPostmanTransport
from arkitekt.postmans.stateful import StatefulPostman
from arkitekt.compositions.base import Arkitekt
import contextvars
from rath import Rath
from koil.composition import Composition


mikro_context = contextvars.ContextVar("mikro_context", default=None)


def replace_keys(data_dict, key_dict):
    new_dict = {}
    if isinstance(data_dict, list):
        dict_value_list = list()
        for inner_dict in data_dict:
            dict_value_list.append(replace_keys(inner_dict, key_dict))
        return dict_value_list
    else:
        for key in data_dict.keys():
            value = data_dict[key]
            new_key = key_dict.get(key, key)
            if isinstance(value, dict) or isinstance(value, list):
                new_dict[new_key] = replace_keys(value, key_dict)
            else:
                new_dict[new_key] = value
        return new_dict
    return new_dict


class ArkitektMockResolver(AsyncMockResolver):
    def __init__(self) -> None:
        super().__init__()
        self.nodeMap = {}
        self.template_map = {}

    async def resolve_node(self, operation: Operation) -> str:
        if operation.variables["package"] != "mock":
            raise NotImplementedError(
                "mock resolver cna only resoplve nodes in the mock package"
            )
        return {
            "package": "rath",
            "interface": "mock",
            "description": "hallo",
            "type": NodeType.FUNCTION,
            "id": "1",
            "name": "mock",
            "args": [],
            "kwargs": [
                {
                    "__typename": "KwargPort",
                    "type": PortType.INT,
                    "key": "a",
                    "default": 0,
                },
                {
                    "__typename": "KwargPort",
                    "type": PortType.INT,
                    "key": "b",
                    "default": 1,
                },
            ],
            "returns": [],
        }

    async def resolve_template(self, operation: Operation) -> str:
        return self.template_map[operation.variables["id"]]

    async def resolve_define(self, operation: Operation) -> str:
        new_node = {
            "id": str(len(self.nodeMap.keys()) + 1),
            "name": operation.variables["definition"]["name"],
            "interface": operation.variables["definition"]["interface"],
            "package": operation.variables["definition"]["package"] or "@mock",
            "description": operation.variables["definition"]["description"],
            "type": operation.variables["definition"]["type"],
            "args": replace_keys(
                operation.variables["definition"]["args"], {"typename": "__typename"}
            ),
            "kwargs": replace_keys(
                operation.variables["definition"]["kwargs"], {"typename": "__typename"}
            ),
            "returns": replace_keys(
                operation.variables["definition"]["returns"], {"typename": "__typename"}
            ),
        }

        self.nodeMap[new_node["id"]] = new_node
        return new_node

    async def resolve_createTemplate(self, operation: Operation) -> str:
        new_template = {
            "id": str(len(self.template_map.keys()) + 1),
            "node": self.nodeMap[operation.variables["node"]],
            "registry": {
                "app": {
                    "name": "johannes",
                }
            },
        }

        self.template_map[new_template["id"]] = new_template
        return new_template

    async def resolve_provision(self, operation: Operation) -> str:
        provision = {
            "id": operation.variables["id"],
            "template": self.template_map[operation.variables["id"]],
            "status": ProvisionStatus.PENDING,
        }

        return provision


class MockArkitektRath(ArkitektRath):
    link: TerminatingLink = Field(
        default_factory=lambda: compose(
            ShrinkingLink(),
            DictingLink(),  # after the shrinking so we can override the dicting
            AsyncMockLink(
                resolver=ArkitektMockResolver().to_dict(),
            ),
        )
    )


class MockAgent(StatefulAgent):
    transport: MockAgentTransport = Field(default_factory=MockAgentTransport)


class MockPostman(StatefulPostman):
    transport: MockPostmanTransport = Field(default_factory=MockPostmanTransport)


class MockArkitekt(Arkitekt):
    rath: MockArkitektRath = Field(default_factory=MockArkitektRath)
    agent: BaseAgent = Field(default_factory=MockAgent)
    postman: MockPostman = Field(default_factory=MockPostman)


class MockRath(Rath):
    def __init__(self) -> None:
        super().__init__(
            link=compose(
                ShrinkingLink(),
                DictingLink(),
                AsyncMockLink(
                    query_resolver=ArkitektMockResolver().to_dict(),
                ),
            )
        )

    async def __aenter__(self) -> None:
        mikro_context.set(self)
        return await super().__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await super().__aexit__(exc_type, exc_val, exc_tb)
        mikro_context.set(None)


def query_current_mikro(query, variables):
    mikro: MockRath = mikro_context.get()
    return mikro.execute(query, variables)


async def aquery_current_mikro(query, variables):
    mikro: MockRath = mikro_context.get()
    return await mikro.aexecute(query, variables)


class MockApp(Composition):
    arkitekt: MockArkitekt = Field(default_factory=MockArkitekt)


class MockComposedApp(MockApp):
    additional_rath: Rath = Field(default_factory=MockRath)
