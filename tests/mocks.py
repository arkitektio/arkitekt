from ctypes import Union
from curses import def_prog_mode
from typing import Any, List, Optional
from arkitekt.agents.stateful import StatefulAgent
from arkitekt.agents.transport.mock import MockAgentTransport
from arkitekt.api.schema import (
    NodeType,
)
from rath.links.testing.mock import AsyncMockResolver, AsyncMockLink
from rath.links.testing.statefulmock import AsyncMockResolver, AsyncStatefulMockLink
from rath.links import ShrinkingLink, DictingLink, SwitchAsyncLink, compose, split
from rath.operation import Operation
from arkitekt.rath import ArkitektRath
from arkitekt.definition.registry import (
    DefinitionRegistry,
    get_current_definition_registry,
)

from arkitekt.structures.registry import (
    StructureRegistry,
    get_current_structure_registry,
)
from arkitekt.postmans.transport.mock import MockPostmanTransport
from arkitekt.postmans.stateful import StatefulPostman
from arkitekt.apps.base import Arkitekt
import contextvars
from rath import Rath
from koil import Koil

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
            "type": NodeType.GENERATOR,
            "id": "1",
            "name": "mock",
        }

    async def resolve_template(self, operation: Operation) -> str:
        return self.template_map[operation.variables["id"]]

    async def resolve_define(self, operation: Operation) -> str:
        new_node = {
            "id": str(len(self.nodeMap.keys()) + 1),
            "name": operation.variables["definition"]["name"],
            "interface": operation.variables["definition"]["interface"],
            "package": operation.variables["definition"]["package"],
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


class MockApp(Arkitekt):
    def __init__(
        self,
        structure_registry: StructureRegistry = None,
        definition_registry: DefinitionRegistry = None,
        **kwargs
    ) -> None:

        structure_registry = structure_registry or get_current_structure_registry()
        definition_registry = definition_registry or get_current_definition_registry()

        rath = ArkitektRath(
            compose(
                ShrinkingLink(),
                DictingLink(),
                SwitchAsyncLink(),  # after the shrinking so we can override the dicting
                AsyncMockLink(
                    resolver=ArkitektMockResolver(),
                ),
            )
        )

        agent_transport = MockAgentTransport()

        agent = StatefulAgent(
            transport=agent_transport,
            definition_registry=definition_registry,
        )

        postman_transport = MockPostmanTransport()

        postman = StatefulPostman(postman_transport)

        super().__init__(
            rath=rath,
            definition_registry=definition_registry,
            structure_registry=structure_registry,
            agent=agent,
            postman=postman,
            **kwargs,
        )


class MikroRath(Rath):
    def __init__(self) -> None:
        super().__init__(
            compose(
                ShrinkingLink(),
                DictingLink(),
                SwitchAsyncLink(),  # after the shrinking so we can override the dicting
                AsyncMockLink(
                    query_resolver=ArkitektMockResolver(),
                ),
            )
        )

    async def __aenter__(self) -> None:
        await super().__aenter__()
        mikro_context.set(self)
        print("Was set my friend")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await super().__aexit__(exc_type, exc_val, exc_tb)
        mikro_context.set(None)


class StatefulMikroRath(Rath):
    def __init__(self) -> None:
        super().__init__(
            compose(
                ShrinkingLink(),
                DictingLink(),
                SwitchAsyncLink(),  # after the shrinking so we can override the dicting
                AsyncStatefulMockLink(
                    query_resolver=ArkitektMockResolver(),
                ),
            )
        )

    async def __aenter__(self) -> None:
        await super().__aenter__()
        mikro_context.set(self)
        print("Was set my friend")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await super().__aexit__(exc_type, exc_val, exc_tb)
        mikro_context.set(None)


def query_current_mikro(query, variables):
    mikro: MikroRath = mikro_context.get()
    return mikro.execute(query, variables)


async def aquery_current_mikro(query, variables):
    mikro: MikroRath = mikro_context.get()
    return await mikro.aexecute(query, variables)
