from arkitekt.agents.transport.base import AgentTransport
from arkitekt.agents.transport.protocols.agent_json import *
from arkitekt.messages import Assignation, Provision, Provision, Unprovision
from arkitekt.api.schema import AssignationStatus, LogLevelInput, ProvisionStatus
from typing import Any, List, Optional, Union
import asyncio
from koil import unkoil


class MockAgentTransport(AgentTransport):
    """A mock transport for an agent

    Args:
        AgentTransport (_type_): _description_
    """

    _inqueue: asyncio.Queue = None

    async def list_assignations(
        self, exclude: Optional[AssignationStatus] = None
    ) -> List[Assignation]:
        return []

    async def list_provisions(
        self, exclude: Optional[ProvisionStatus] = None
    ) -> List[Provision]:
        return []

    async def __aenter__(self):
        self._inqueue = asyncio.Queue()

    async def change_assignation(
        self,
        id: str,
        status: AssignationStatus = None,
        message: str = None,
        returns: List[Any] = None,
    ):
        await self._inqueue.put(
            AssignationChangedMessage(
                assignation=id, status=status, message=message, returns=returns
            )
        )

    async def log_to_assignation(
        self, id: str, level: LogLevelInput = None, message: str = None
    ):
        print(f"{id} {level} {message}")

    async def log_to_provision(
        self, id: str, level: LogLevelInput = None, message: str = None
    ):
        print(f"{id} {level} {message}")

    async def change_provision(
        self,
        id: str,
        status: ProvisionStatus = None,
        message: str = None,
        mode: ProvisionMode = None,
    ):
        await self._inqueue.put(
            ProvisionChangedMessage(
                provision=id, status=status, message=message, mode=mode
            )
        )

    async def adelay(
        self, message: Union[Assignation, Provision, Unprovision, Unassignation]
    ):
        await self._abroadcast(message)

    def delay(self, message: Union[Assignation, Provision, Unprovision, Unassignation]):
        return unkoil(self.adelay, message)

    def receive(self, *args, **kwargs):
        return unkoil(self.areceive, *args, **kwargs)

    async def areceive(self, timeout=None):
        if timeout:
            return await asyncio.wait_for(self._inqueue.get(), timeout)
        return await self._inqueue.get()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for item in range(self._inqueue.qsize()):
            self._inqueue.task_done()

    class Config:
        underscore_attrs_are_private = True
        arbitrary_types_allowed = True
