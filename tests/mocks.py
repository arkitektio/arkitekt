import asyncio
from typing import Any, List, Optional
from arkitekt.agents.messages import Assignation, Provision, Provision, Unprovision
from arkitekt.api.schema import AssignationStatus, NodeType, ProvisionStatus
from arkitekt.agents.transport.base import AgentTransport
from rath.links.testing.mock import AsyncMockResolver
from rath.operation import Operation


class MockTransport(AgentTransport):
    """A mock transport for an agent

    Args:
        AgentTransport (_type_): _description_
    """

    async def list_assignations(
        self, exclude: Optional[AssignationStatus] = None
    ) -> List[Assignation]:
        return [
            Assignation(
                assignation="1", provision="1", reservation="1", args=[], kwargs={}
            ),
            Assignation(
                assignation="2", provision="2", reservation="1", args=[], kwargs={}
            ),
        ]

    async def list_provisions(
        self, exclude: Optional[ProvisionStatus] = None
    ) -> List[Provision]:
        return [
            Provision(provision="1", template="1"),
            Provision(provision="2", template="1"),
        ]

    async def aconnect(self):
        self.task = asyncio.create_task(self.send_fake_assignation())

    async def change_assignation(
        self,
        id: str,
        status: AssignationStatus = None,
        message: str = None,
        result: List[Any] = None,
    ):
        pass

    async def send_fake_assignation(self):
        await asyncio.sleep(1)
        await self.broadcast(
            Assignation(
                assignation="1", provision="1", reservation="1", args=[], kwargs={}
            )
        )
        await asyncio.sleep(1)

    async def disconnect(self):
        self.task.cancel()

        try:
            await self.task
        except asyncio.CancelledError as e:
            pass


class ArkitektQueryResolver(AsyncMockResolver):
    async def resolve_node(self, operation: Operation) -> str:
        return {
            "package": "rath",
            "interface": "mock",
            "description": "hallo",
            "type": NodeType.GENERATOR,
            "id": "1",
            "name": "mock",
        }


class ArkitektMutationResolver(AsyncMockResolver):
    def __init__(self) -> None:
        super().__init__()
        self.nodeMap = {}
        self.template_map = {}

    async def resolve_define(self, operation: Operation) -> str:
        new_node = {
            "id": str(len(self.nodeMap.keys()) + 1),
            "name": operation.variables["definition"]["name"],
            "interface": operation.variables["definition"]["interface"],
            "package": operation.variables["definition"]["package"],
            "description": operation.variables["definition"]["description"],
            "type": operation.variables["definition"]["type"],
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
