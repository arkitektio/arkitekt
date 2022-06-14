from abc import abstractmethod
from typing import Any, Awaitable, Callable, List, Optional, Union

from arkitekt.messages import Assignation, Unassignation, Provision, Unprovision
from arkitekt.api.schema import (
    LogLevelInput,
    ProvisionMode,
    ProvisionStatus,
    AssignationStatus,
)
from koil.composition import KoiledModel
from koil.types import Contextual


class AgentTransport(KoiledModel):
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

    _abroadcast: Contextual[
        Callable[
            [Union[Assignation, Unassignation, Unprovision, Provision]], Awaitable[None]
        ]
    ]

    @property
    def connected(self):
        return NotImplementedError("Implement this method")

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
    async def log_to_provision(
        self,
        id: str,
        level: LogLevelInput = None,
        message: str = None,
    ):
        raise NotImplementedError("This is an abstract Base Class")

    @abstractmethod
    async def log_to_assignation(
        self,
        id: str,
        level: LogLevelInput = None,
        message: str = None,
    ):
        raise NotImplementedError("This is an abstract Base Class")

    @abstractmethod
    async def list_assignations(
        self, exclude: Optional[AssignationStatus] = None
    ) -> List[Assignation]:
        raise NotImplementedError("This is an abstract Base Class")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    class Config:
        underscore_attrs_are_private = True
        arbitrary_types_allowed = True
        copy_on_model_validation = False