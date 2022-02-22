from .stateful import StatefulPostman
from arkitekt.api.schema import AssignationStatus, ReservationStatus, ReserveParamsInput
import asyncio
from typing import Union
from arkitekt.traits.node import Reserve


class ReservationContract:
    def __init__(
        self,
        postman: StatefulPostman,
        node: Union[str, Reserve],
        params: ReserveParamsInput,
    ):
        self.postman = postman
        if isinstance(node, Reserve):
            self.node_id = node.id
        else:
            assert isinstance(node, str), "Node must be a string or a Node"
            self.node_id = node
        self.params = params
        self.reservation = None
        self.postman = postman

    async def assign(self, *args, **kwargs):
        assert self.reservation, "We never entered the context manager"
        assert (
            self.reservation.status == ReservationStatus.ACTIVE
        ), "Reservation is not active"

        _ass_queue = asyncio.Queue()
        ass = await self.postman.aassign(self.reservation.reservation, args, kwargs)
        self.postman.register_assignation_queue(ass.assignation, _ass_queue)

        while True:  # Waiting for assignation
            ass = await _ass_queue.get()
            if ass.status == AssignationStatus.RETURNED:
                self.postman.unregister_assignation_queue(ass.assignation)
                return ass.returns

    async def watch_updates(self):
        try:

            if self.reservation.status == ReservationStatus.ACTIVE:
                self._enter_future.set_result(True)

            while True:
                self.reservation = await self._updates_queue.get()
                if self.reservation.status == ReservationStatus.ACTIVE:
                    if self._enter_future:
                        self._enter_future.set_result(True)

        except asyncio.CancelledError:
            pass

    async def __aenter__(self):
        self.reservation = await self.postman.areserve(self.node_id, self.params)
        self._updates_queue = asyncio.Queue()
        self._enter_future = asyncio.Future()
        self.postman.register_reservation_queue(
            self.reservation.reservation, self._updates_queue
        )
        self.updates_watcher = asyncio.create_task(self.watch_updates())
        await self._enter_future  # Waiting to enter

        return self

    async def __aexit__(self, *args, **kwargs):
        self.updates_watcher.cancel()

        try:
            await self.updates_watcher
        except asyncio.CancelledError:
            pass

        await self.postman.aunreserve(self.reservation.reservation)
        self.postman.unregister_reservation_queue(self.reservation.reservation)


def use(
    node: str, params: dict = None, postman: StatefulPostman = None
) -> ReservationContract:
    return ReservationContract(postman, node, params)
