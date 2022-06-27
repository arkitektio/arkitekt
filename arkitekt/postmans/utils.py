from ast import Assign
from random import Random, random
from typing import Awaitable, Callable, Optional
import uuid

from pydantic import Field
from arkitekt.messages import Assignation, Reservation
from arkitekt.postmans.vars import current_postman
from arkitekt.structures.registry import get_current_structure_registry
from koil.composition import KoiledModel
from koil.types import ContextBool
from .stateful import StatefulPostman
from arkitekt.api.schema import (
    AssignationLogLevel,
    AssignationStatus,
    ReservationStatus,
    ReserveParamsInput,
)
import asyncio
from arkitekt.traits.node import Reserve
from koil import unkoil
import logging
from arkitekt.structures.serialization.postman import shrink_inputs, expand_outputs


logger = logging.getLogger(__name__)


class ReservationContract(KoiledModel):
    # TODO:Assert that we can actually assign to this? validating that all of the nodes inputs are
    # registered in the structure registry?
    node: Reserve
    params: ReserveParamsInput = Field(default_factory=ReserveParamsInput)
    auto_unreserve: bool = False
    shrink_inputs: bool = True
    expand_outputs: bool = True
    res_log: Optional[
        Callable[[Reservation, AssignationLogLevel, str], Awaitable[None]]
    ] = Field(default=None, exclude=True)

    active: ContextBool = False
    _reservation: Reservation = None

    async def aassign(
        self,
        *args,
        structure_registry=None,
        alog: Callable[[Assignation, AssignationLogLevel, str], Awaitable[None]] = None,
        **kwargs,
    ):
        raise NotImplementedError("Should be implemented by subclass")

    async def _alog(self, assignation, level, msg):
        if self.ass_log:  # pragma: no branch
            await self.ass_log(assignation, level, msg)

    async def _rlog(self, level, msg):
        if self.res_log:  # pragma: no branch
            await self.res_log(self._reservation, level, msg)

    def assign(self, *args, **kwargs):
        return unkoil(self.aassign, *args, **kwargs)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            callable: lambda q: repr(q),
        }


class use(ReservationContract):
    postman: Optional[StatefulPostman] = None
    _reservation: Reservation = None
    _enter_future: asyncio.Future = None
    _exit_future: asyncio.Future = None
    _updates_queue: asyncio.Queue = None
    _updates_watcher: asyncio.Task = None

    async def aassign(
        self,
        *args,
        structure_registry=None,
        alog: Callable[[Assignation, AssignationLogLevel, str], Awaitable[None]] = None,
        **kwargs,
    ):
        assert self._reservation, "We never entered the context manager"
        assert (
            self._reservation.status == ReservationStatus.ACTIVE
        ), "Reservation is not active"

        structure_registry = structure_registry or get_current_structure_registry()
        _ass_queue = asyncio.Queue()

        shrinked_args, shrinked_kwargs = (
            await shrink_inputs(
                self.node, args, kwargs, structure_registry=structure_registry
            )
            if self.shrink_inputs
            else (args, kwargs)
        )

        ass = await self.postman.aassign(
            self._reservation.reservation, shrinked_args, shrinked_kwargs
        )
        self.postman.register_assignation_queue(ass.assignation, _ass_queue)
        logger.info(f"Listening to assignation updates for {ass}")
        try:
            while True:  # Waiting for assignation
                ass = await _ass_queue.get()
                logger.info(f"Reservation Context: {ass}")
                if ass.status == AssignationStatus.RETURNED:
                    self.postman.unregister_assignation_queue(ass.assignation)
                    outputs = (
                        await expand_outputs(
                            self.node,
                            ass.returns,
                            structure_registry=structure_registry,
                        )
                        if self.expand_outputs
                        else ass.returns
                    )
                    return outputs

                if ass.status == AssignationStatus.CRITICAL:
                    self.postman.unregister_assignation_queue(ass.assignation)
                    raise Exception(f"Critical error: {ass.message}")
        except asyncio.CancelledError as e:
            await self.postman.aunassign(ass.assignation)

            ass = await asyncio.wait_for(_ass_queue.get(), timeout=2)
            if ass.status == AssignationStatus.CANCELLED:
                logger.info("Wonderfully cancelled that assignation!")
                raise e

            raise Exception(f"Critical error: {ass}")

    async def watch_updates(self):
        try:
            if self._reservation.status == ReservationStatus.ACTIVE:
                self._enter_future.set_result(True)

            while True:
                self._reservation = await self._updates_queue.get()
                if self._reservation.status == ReservationStatus.ACTIVE:
                    if self._enter_future and not self._enter_future.done():
                        self._enter_future.set_result(True)

        except asyncio.CancelledError:
            pass

    async def __aenter__(self):
        self.postman = self.postman or current_postman.get()
        logger.info(f"Trying to reserve {self.node}")
        self._reservation = await self.postman.areserve(self.node.id, self.params)
        logger.info(f"Waiting for Reservation {self._reservation}")
        self._updates_queue = asyncio.Queue()
        self._enter_future = asyncio.Future()

        self.postman.register_reservation_queue(
            self._reservation.reservation, self._updates_queue
        )
        self._updates_watcher = asyncio.create_task(self.watch_updates())
        await self._enter_future  # Waiting to enter
        self.active = True
        return self

    async def __aexit__(self, *args, **kwargs):
        self.active = False

        if self.auto_unreserve:

            unreservation = await asyncio.wait_for(
                self.postman.aunreserve(self._reservation.reservation), timeout=1
            )
            logger.info(f"Unreserved {unreservation}")

        self._updates_watcher.cancel()

        try:
            await self._updates_watcher
        except asyncio.CancelledError:
            pass

        self.postman.unregister_reservation_queue(self._reservation.reservation)

    class Config:
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True


class mockuse(ReservationContract):
    random_sleep: float = Field(default_factory=random)

    async def __aenter__(self):
        self.active = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.active = False

    async def aassign(
        self,
        *args,
        structure_registry=None,
        alog: Callable[[Assignation, AssignationLogLevel, str], Awaitable[None]] = None,
        **kwargs,
    ):
        assert self.active, "We never entered the context manager"
        if alog:
            await alog(
                Assignation(assignation=str(uuid.uuid4())),
                AssignationLogLevel.INFO,
                "Mock assignation",
            )
        await asyncio.sleep(self.random_sleep)
        print("Assignment Done")
        return args
