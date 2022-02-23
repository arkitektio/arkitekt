from abc import abstractmethod
from typing import Any, List, Optional, Union
from arkitekt.messages import Assignation, Unassignation, Provision, Unprovision
from arkitekt.api.schema import ProvisionMode, ProvisionStatus, AssignationStatus


class AgentTransport:
    """Agent Transport

    A Transport is a means of communicating with an Agent. It is responsible for sending
    and receiving messages from the backend. It needs to implement the following methods:

    list_provision: Getting the list of active provisions from the backend. (depends on the backend)
    list_assignation: Getting the list of active assignations from the backend. (depends on the backend)

    change_assignation: Changing the status of an assignation. (depends on the backend)
    change_provision: Changing the status of an provision. (depends on the backend)

    broadcast: Configuring the callbacks for the transport on new assignation, unassignation provision and unprovison.

    if it is a stateful connection it can also implement the following methods:

    aconnect
    adisconnect

    """

    async def aconnect(self):
        pass

    async def adisconnect(self):
        pass

    @abstractmethod
    def broadcast(
        self, message: Union[Assignation, Unassignation, Provision, Unprovision]
    ):
        raise NotImplementedError("This is an abstract Base Class")

    @abstractmethod
    async def list_provisions(
        self, exclude: Optional[ProvisionStatus] = None
    ) -> List[Provision]:
        raise NotImplementedError("This is an abstract Base Class")

    @abstractmethod
    async def change_provision(
        self,
        id: str,
        status: ProvisionStatus = None,
        message: str = None,
        mode: ProvisionMode = None,
    ):
        raise NotImplementedError("This is an abstract Base Class")

    @abstractmethod
    async def change_assignation(
        self,
        id: str,
        status: AssignationStatus = None,
        message: str = None,
        returns: List[Any] = None,
    ):
        raise NotImplementedError("This is an abstract Base Class")

    @abstractmethod
    async def list_assignations(
        self, exclude: Optional[AssignationStatus] = None
    ) -> List[Assignation]:
        raise NotImplementedError("This is an abstract Base Class")

    async def __aenter__(self):
        await self.aconnect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.adisconnect()
