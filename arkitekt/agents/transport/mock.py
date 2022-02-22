from arkitekt.agents.transport.base import AgentTransport
from arkitekt.messages import Assignation, Provision, Provision, Unprovision
from arkitekt.api.schema import AssignationStatus, ProvisionStatus
from typing import Any, List, Optional
import asyncio


class MockAgentTransport(AgentTransport):
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
