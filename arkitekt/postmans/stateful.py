from typing import Any, Dict, List, Union
from arkitekt.api.schema import AssignationStatus, ReservationStatus

from arkitekt.messages import Assignation, Reservation
from arkitekt.postmans.base import BasePostman
import asyncio
from pydantic import Field


class StatefulPostman(BasePostman):

    assignations: Dict[str, Assignation] = Field(default_factory=dict)
    reservations: Dict[str, Reservation] = Field(default_factory=dict)

    _res_update_queues: Dict[str, asyncio.Queue] = {}
    _ass_update_queues: Dict[str, asyncio.Queue] = {}

    async def aconnect(self):
        await super().aconnect()

        data = await self.transport.alist_reservations()
        self.reservations = {res.reservation: res for res in data}

        data = await self.transport.alist_assignations()
        self.assignations = {ass.assignation: ass for ass in data}

    async def areserve(self, node: str, params: dict = None) -> Reservation:
        reservation = await self.transport.areserve(node, params)
        self.reservations[reservation.reservation] = reservation
        return reservation

    async def aunreserve(self, reservation_id: str) -> Reservation:
        unreservation = await self.transport.aunreserve(reservation_id)
        self.reservations[
            unreservation.reservation
        ].status = ReservationStatus.CANCELING
        return self.reservations[unreservation.reservation]

    async def aassign(
        self,
        reservation: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        persist=True,
        log=False,
    ) -> Assignation:
        assignation = await self.transport.aassign(
            reservation, args, kwargs, persist, log
        )
        self.assignations[assignation.assignation] = assignation
        return assignation

    async def aunassign(
        self,
        assignation: str,
    ) -> Assignation:
        print(assignation)
        unassignation = await self.transport.aunassign(assignation)
        self.assignations[
            unassignation.assignation
        ].status = AssignationStatus.CANCELING
        return unassignation

    def register_reservation_queue(self, res_id: str, queue: asyncio.Queue):
        self._res_update_queues[res_id] = queue

    def register_assignation_queue(self, ass_id: str, queue: asyncio.Queue):
        self._ass_update_queues[ass_id] = queue

    async def abroadcast(self, message: Union[Assignation, Reservation]):
        if isinstance(message, Assignation):
            self.assignations[message.assignation].update(message)
            if message.assignation in self._ass_update_queues:
                await self._ass_update_queues[message.assignation].put(
                    self.assignations[message.assignation]
                )
        elif isinstance(message, Reservation):
            self.reservations[message.reservation].update(message)
            if message.reservation in self._res_update_queues:
                await self._res_update_queues[message.reservation].put(
                    self.reservations[message.reservation]
                )

        else:
            raise Exception("Unknown message type")

    def unregister_reservation_queue(self, res_id: str):
        del self._res_update_queues[res_id]

    def unregister_assignation_queue(self, ass_id: str):
        del self._ass_update_queues[ass_id]
