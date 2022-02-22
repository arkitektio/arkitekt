from typing import Any, Dict, List, Union

from pytest import param
from arkitekt.messages import Assignation, Reservation
from arkitekt.postmans.base import Postman
from arkitekt.postmans.transport.base import PostmanTransport
from arkitekt.api.schema import ReservationStatus, ReserveParamsInput
import asyncio


class StatefulPostman(Postman):
    def __init__(self, transport: PostmanTransport) -> None:
        super().__init__(transport)
        self.assignations: Dict[str, Assignation] = {}
        self.reservations: Dict[str, Reservation] = {}

        self.res_update_queues: Dict[str, asyncio.Queue] = {}
        self.ass_update_queues: Dict[str, asyncio.Queue] = {}

    async def aconnect(self):
        await self.transport.aconnect()

        data = await self.transport.alist_reservations()
        self.reservations = {res.reservation: res for res in data}

        data = await self.transport.alist_assignations()
        self.assignations = {ass.assignation: ass for ass in data}

    async def areserve(self, node: str, params: dict = None) -> Reservation:
        reservation = await self.transport.areserve(node, params)
        self.reservations[reservation.reservation] = reservation
        return reservation

    async def aunreserve(self, reservation_id: str) -> Reservation:
        reservation = await self.transport.aunreserve(reservation_id)
        self.reservations[reservation.reservation] = reservation
        return reservation

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

    def register_reservation_queue(self, res_id: str, queue: asyncio.Queue):
        self.res_update_queues[res_id] = queue

    def register_assignation_queue(self, ass_id: str, queue: asyncio.Queue):
        self.ass_update_queues[ass_id] = queue

    async def abroadcast(self, message: Union[Assignation, Reservation]):
        if isinstance(message, Assignation):

            self.assignations[message.assignation].update(message)
            if message.assignation in self.ass_update_queues:
                await self.ass_update_queues[message.assignation].put(
                    self.assignations[message.assignation]
                )
        elif isinstance(message, Reservation):

            self.reservations[message.reservation].update(message)
            if message.reservation in self.res_update_queues:
                await self.res_update_queues[message.reservation].put(
                    self.reservations[message.reservation]
                )

        else:
            raise Exception("Unknown message type")

    def unregister_reservation_queue(self, res_id: str):
        del self.res_update_queues[res_id]

    def unregister_assignation_queue(self, ass_id: str):
        del self.ass_update_queues[ass_id]
