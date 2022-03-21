from arkitekt.postmans.vars import current_postman
from arkitekt.structures.registry import get_current_structure_registry
from koil.decorators import koilable
from .stateful import StatefulPostman
from arkitekt.api.schema import AssignationStatus, ReservationStatus, ReserveParamsInput
import asyncio
from arkitekt.traits.node import Reserve
from koil import unkoil
import logging
from arkitekt.structures.serialization.postman import shrink_inputs, expand_outputs


logger = logging.getLogger(__name__)


@koilable(fieldname="_koil", add_connectors=True)
class ReservationContract:
    def __init__(
        self,
        node: Reserve,
        postman: StatefulPostman = None,
        params: ReserveParamsInput = None,
        auto_unreserve: bool = True,
    ):
        self.postman = postman
        if isinstance(node, Reserve):
            self.node = node
        else:
            raise NotImplementedError("You need to pass a Reservable Instance")
        self.params = params or ReserveParamsInput()
        self.reservation = None
        self.postman = None
        self.auto_unreserve = auto_unreserve

    async def aassign(self, *args, structure_registry=None, **kwargs):
        assert self.reservation, "We never entered the context manager"
        assert (
            self.reservation.status == ReservationStatus.ACTIVE
        ), "Reservation is not active"

        structure_registry = structure_registry or get_current_structure_registry()
        _ass_queue = asyncio.Queue()

        shrinked_args, shrinked_kwargs = await shrink_inputs(
            self.node, args, kwargs, structure_registry=structure_registry
        )

        ass = await self.postman.aassign(
            self.reservation.reservation, shrinked_args, shrinked_kwargs
        )
        self.postman.register_assignation_queue(ass.assignation, _ass_queue)
        logger.info(f"Listening to assignation updates for {ass}")
        while True:  # Waiting for assignation
            ass = await _ass_queue.get()
            logger.info(f"Reservation Context: {ass}")
            if ass.status == AssignationStatus.RETURNED:
                self.postman.unregister_assignation_queue(ass.assignation)
                return await expand_outputs(
                    self.node, ass.returns, structure_registry=structure_registry
                )

            if ass.status == AssignationStatus.CRITICAL:
                self.postman.unregister_assignation_queue(ass.assignation)
                raise Exception(f"Critical error: {ass.message}")

    def assign(self, *args, **kwargs):
        return unkoil(self.aassign, *args, **kwargs)

    async def watch_updates(self):
        try:
            if self.reservation.status == ReservationStatus.ACTIVE:
                self._enter_future.set_result(True)

            while True:
                self.reservation = await self._updates_queue.get()
                if self.reservation.status == ReservationStatus.ACTIVE:
                    if self._enter_future and not self._enter_future.done():
                        self._enter_future.set_result(True)

        except asyncio.CancelledError:
            pass

    async def __aenter__(self):
        self.postman = self.postman or current_postman.get()
        logger.info(f"Trying to reserve {self.node}")
        self.reservation = await self.postman.areserve(self.node.id, self.params)
        logger.info(f"Waiting for Reservation {self.reservation}")
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

        if self.auto_unreserve:
            await asyncio.wait_for(
                self.postman.aunreserve(self.reservation.reservation), timeout=1
            )
        self.postman.unregister_reservation_queue(self.reservation.reservation)

    def __enter__(self) -> "ReservationContract":
        ...


def use(
    node: str,
    params: ReserveParamsInput = None,
    postman: StatefulPostman = None,
    auto_unreserve=True,
) -> ReservationContract:
    return ReservationContract(
        node, postman=postman, params=params, auto_unreserve=auto_unreserve
    )
