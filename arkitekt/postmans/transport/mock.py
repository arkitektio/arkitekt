from arkitekt.postmans.transport.base import PostmanTransport
from arkitekt.messages import (
    Assignation,
    Reservation,
    Unassignation,
    Unreservation,
)
from arkitekt.api.schema import (
    AssignationStatus,
    ReservationStatus,
    ReserveParamsInput,
)
from typing import Any, Dict, List, Optional, Union
import asyncio
import random
from pydantic import Field
from koil import unkoil


class MockAutoresolvingPostmanTransport(PostmanTransport):
    """A mock transport for an agent

    Args:
        AgentTransport (_type_): _description_
    """

    assignationState: Dict[str, Assignation] = Field(default_factory=dict)
    unassignationState: Dict[str, Unassignation] = Field(default_factory=dict)
    unreservationState: Dict[str, Unreservation] = Field(default_factory=dict)
    reservationState: Dict[str, Reservation] = Field(default_factory=dict)

    _task: Optional[asyncio.Task] = None

    async def alist_assignations(
        self, exclude: Optional[AssignationStatus] = None
    ) -> List[Assignation]:
        return self.assignationState.values()

    async def alist_reservations(
        self, exclude: Optional[ReservationStatus] = None
    ) -> List[Reservation]:
        return self.reservationState.values()

    async def __aenter__(self):
        self._task = asyncio.create_task(self.aresolve_reservations())

    async def aassign(
        self,
        reservation: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        persist=True,
        log=False,
    ) -> Assignation:

        assignation = Assignation(
            assignation=str(len(self.assignationState) + 1),
            reservation=reservation,
            args=args,
            kwargs=kwargs,
            status=AssignationStatus.PENDING,
        )
        self.assignationState[assignation.assignation] = assignation
        return assignation

    async def areserve(
        self, node: str, params: ReserveParamsInput = None
    ) -> Reservation:
        reservation = Reservation(
            reservation=str(len(self.reservationState) + 1),
            node=node,
            status=ReservationStatus.ROUTING,
        )
        self.reservationState[reservation.reservation] = reservation
        return reservation

    async def aunreserve(self, reservation: str) -> Unreservation:
        self.reservationState[reservation].update(
            Reservation(reservation=reservation, status=ReservationStatus.CANCELLED)
        )
        return Unreservation(reservation=reservation)

    async def aunassign(self, assignation: str) -> Unassignation:
        self.assignationState[assignation].update(
            Assignation(assignation=assignation, status=AssignationStatus.CANCELLED)
        )
        return assignation

    async def aresolve_reservations(self):

        while True:

            await asyncio.sleep(0.1)

            ress = [
                res
                for key, res in self.reservationState.items()
                if res.status == ReservationStatus.ROUTING
            ]
            if ress:
                res = random.choice(ress)
                res.status = ReservationStatus.ACTIVE

                self.reservationState[res.reservation] = res
                await self._abroadcast(res)

            asss = [
                ass
                for key, ass in self.assignationState.items()
                if ass.status == AssignationStatus.PENDING
            ]

            if asss:
                ass = random.choice(asss)
                ass.status = AssignationStatus.RETURNED
                ass.returns = []

                self.assignationState[ass.assignation] = ass
                await self._abroadcast(ass)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._task.cancel()

        try:
            await self._task
        except asyncio.CancelledError as e:
            pass

    class Config:
        underscore_attrs_are_private = True


class MockPostmanTransport(PostmanTransport):

    assignationState: Dict[str, Assignation] = Field(default_factory=dict)
    unassignationState: Dict[str, Unassignation] = Field(default_factory=dict)
    unreservationState: Dict[str, Unreservation] = Field(default_factory=dict)
    reservationState: Dict[str, Reservation] = Field(default_factory=dict)

    _inqueue: asyncio.Queue = None

    async def alist_assignations(
        self, exclude: Optional[AssignationStatus] = None
    ) -> List[Assignation]:
        return []

    async def alist_reservations(
        self, exclude: Optional[ReservationStatus] = None
    ) -> List[Reservation]:
        return []

    async def __aenter__(self):
        self._inqueue = asyncio.Queue()

    async def aassign(
        self,
        reservation: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        persist=True,
        log=False,
    ) -> Assignation:

        assignation = Assignation(
            assignation=str(len(self.assignationState) + 1),
            reservation=reservation,
            args=args,
            kwargs=kwargs,
            status=AssignationStatus.PENDING,
        )
        self.assignationState[assignation.assignation] = assignation
        await self._inqueue.put(assignation)
        return assignation

    async def areserve(
        self, node: str, params: ReserveParamsInput = None
    ) -> Reservation:
        print("Called")
        reservation = Reservation(
            reservation=str(len(self.reservationState) + 1),
            node=node,
            status=ReservationStatus.ROUTING,
        )
        self.reservationState[reservation.reservation] = reservation
        await self._inqueue.put(reservation)
        return reservation

    async def aunreserve(self, reservation: str) -> Unreservation:
        unreservation = Unreservation(reservation=reservation)
        await self._inqueue.put(unreservation)
        return unreservation

    async def aunassign(self, assignation: str) -> Unassignation:
        unassignation = Unassignation(assignation=assignation)
        await self._inqueue.put(Unassignation(assignation=assignation))
        return unassignation

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for item in range(self._inqueue.qsize()):
            self._inqueue.task_done()

    async def adelay(
        self, message: Union[Assignation, Reservation, Unreservation, Unassignation]
    ):
        await self._abroadcast(message)

    async def areceive(self, timeout=None):
        if timeout:
            return await asyncio.wait_for(self._inqueue.get(), timeout)
        return await self._inqueue.get()

    def delay(
        self, message: Union[Assignation, Reservation, Unreservation, Unassignation]
    ):
        return unkoil(self.adelay, message)

    def receive(self, *args, **kwargs):
        return unkoil(self.areceive, *args, **kwargs)

    class Config:
        underscore_attrs_are_private = True
        arbitrary_types_allowed = True
