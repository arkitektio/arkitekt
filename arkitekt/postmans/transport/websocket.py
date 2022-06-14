import asyncio
import json

import websockets
from arkitekt.postmans.transport.base import PostmanTransport
from typing import Any, Awaitable, Callable, Dict, List, Optional
from arkitekt.messages import Assignation, Reservation
from arkitekt.postmans.transport.errors import (
    AssignDeniedError,
    AssignationListDeniedError,
    PostmanTransportException,
    ReservationListDeniedError,
    ReserveDeniedError,
    UnassignDeniedError,
    UnreserveDeniedError,
)
from pydantic import Field
from .protocols.postman_json import *
import logging
from websockets.exceptions import ConnectionClosedError, InvalidStatusCode

logger = logging.getLogger(__name__)


async def token_loader():
    raise NotImplementedError(
        "Websocket transport does need a defined token_loader on Connection"
    )


class CorrectableConnectionFail(PostmanTransportException):
    pass


class DefiniteConnectionFail(PostmanTransportException):
    pass


class WebsocketPostmanTransport(PostmanTransport):
    endpoint_url: str
    token_loader: Callable[[], Awaitable[str]] = Field(exclude=True)
    max_retries = 5
    time_between_retries = 5
    allow_reconnect = True

    auto_connect = True

    _futures: Dict[str, asyncio.Future] = {}
    _connected = False
    _healthy = False
    _send_queue: Optional[asyncio.Queue] = None
    _connection_task: Optional[asyncio.Task] = None

    async def aconnect(self):
        assert (
            self._abroadcast is not None
        ), "Broadcast must be defined (either overwrite abroadcast or pass this in constructor of transport)"

        assert self.instance_id, "Needs an instance id"
        self._send_queue = asyncio.Queue()
        self._connection_task = asyncio.create_task(self.websocket_loop())
        self._connected = True

    async def websocket_loop(self, retry=0, reload_token=False):
        send_task = None
        receive_task = None
        try:
            try:
                token = await self.token_loader(force_refresh=reload_token)

                async with websockets.connect(
                    f"{self.endpoint_url}?token={token}&instance_id={self.instance_id}"
                ) as client:

                    logger.info("Postman on Websockets connected")

                    send_task = asyncio.create_task(self.sending(client))
                    receive_task = asyncio.create_task(self.receiving(client))

                    self._healthy = True
                    done, pending = await asyncio.wait(
                        [send_task, receive_task],
                        return_when=asyncio.FIRST_EXCEPTION,
                    )
                    self._healthy = True

                    for task in pending:
                        task.cancel()

                    for task in done:
                        raise task.exception()

            except InvalidStatusCode as e:
                logger.warning(
                    f"Websocket Connect was denied. Trying to reload token {token}",
                    exc_info=True,
                )
                reload_token = True
                raise CorrectableConnectionFail from e

            except ConnectionClosedError as e:
                logger.warning("Websocket was closed", exc_info=True)
                raise CorrectableConnectionFail from e

            except Exception as e:
                logger.warning("Websocket excepted. Trying to recover", exc_info=True)
                raise CorrectableConnectionFail from e

        except CorrectableConnectionFail as e:
            logger.info(f"Trying to Recover from Exception {e}")
            if retry > self.max_retries or not self.allow_reconnect:
                raise DefiniteConnectionFail("Exceeded Number of Retries")

            await asyncio.sleep(self.time_between_retries)
            logger.info(f"Retrying to connect")
            await self.websocket_loop(retry=retry + 1, reload_token=reload_token)

        except DefiniteConnectionFail as e:
            logger.error("Websocket excepted closed definetely", exc_info=True)
            self.connection_dead = False
            raise e

        except asyncio.CancelledError as e:
            logger.info("Websocket got cancelled. Trying to shutdown graceully")
            if send_task and receive_task:
                send_task.cancel()
                receive_task.cancel()

            cancellation = await asyncio.gather(
                send_task, receive_task, return_exceptions=True
            )
            raise e

    async def sending(self, client):
        try:
            while True:
                message = await self._send_queue.get()
                await client.send(message)
                self._send_queue.task_done()
        except asyncio.CancelledError as e:
            logger.info("Sending Task sucessfully Cancelled")

    async def receiving(self, client):
        try:
            async for message in client:
                await self.receive(message)
        except asyncio.CancelledError as e:
            logger.info("Receiving Task sucessfully Cancelled")

    async def receive(self, message):
        json_dict = json.loads(message)
        if "type" in json_dict:
            type = json_dict["type"]
            id = json_dict["id"]
            logger.debug(str(json_dict))

            # State Layer
            if type == PostmanSubMessageTypes.ASSIGN_UPDATE:
                await self._abroadcast(AssignSubUpdate(**json_dict))

            if type == PostmanSubMessageTypes.RESERVE_UPDATE:
                await self._abroadcast(ReserveSubUpdate(**json_dict))

            if type == PostmanMessageTypes.LIST_ASSIGNATION_REPLY:
                self._futures[id].set_result(AssingListReply(**json_dict))
            if type == PostmanMessageTypes.LIST_ASSIGNATION_DENIED:
                self._futures[id].set_exception(
                    AssignationListDeniedError(json_dict["error"])
                )

            if type == PostmanMessageTypes.LIST_RESERVATION_REPLY:
                self._futures[id].set_result(ReserveListReply(**json_dict))
            if type == PostmanMessageTypes.LIST_RESERVATION_DENIED:
                self._futures[id].set_exception(
                    ReservationListDeniedError(json_dict["error"])
                )

            if type == PostmanMessageTypes.ASSIGN_REPLY:
                self._futures[id].set_result(AssignPubReply(**json_dict))
            if type == PostmanMessageTypes.ASSIGN_DENIED:
                self._futures[id].set_exception(AssignDeniedError(json_dict["error"]))

            if type == PostmanMessageTypes.UNASSIGN_REPLY:
                self._futures[id].set_result(UnassignPubReply(**json_dict))
            if type == PostmanMessageTypes.UNASSIGN_DENIED:
                self._futures[id].set_exception(UnassignDeniedError(json_dict["error"]))

            if type == PostmanMessageTypes.RESERVE_REPLY:
                self._futures[id].set_result(ReservePubReply(**json_dict))
            if type == PostmanMessageTypes.RESERVE_DENIED:
                self._futures[id].set_exception(ReserveDeniedError(json_dict["error"]))

            if type == PostmanMessageTypes.UNRESERVE_REPLY:
                self._futures[id].set_result(UnreservePubReply(**json_dict))
            if type == PostmanMessageTypes.UNRESERVE_DENIED:
                self._futures[id].set_exception(
                    UnreserveDeniedError(json_dict["error"])
                )

        else:
            logger.error(f"Error {json_dict}")

    async def awaitaction(self, action: JSONMessage):
        if not self._connected:
            assert (
                self.auto_connect
            ), "Websocket not connected, and autoconnect to false"
            await self.aconnect()

        if action.id in self._futures:
            raise ValueError("Action already has a future")

        future = asyncio.Future()
        self._futures[action.id] = future
        await self._send_queue.put(action.json())
        return await future

    async def alist_reservations(
        self, exclude: Optional[ReservationStatus] = None
    ) -> List[Reservation]:
        prov_list_reply: ReserveListReply = await self.awaitaction(
            ReserveList(exclude=exclude)
        )
        return prov_list_reply.reservations

    async def aassign(
        self,
        reservation: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        persist=True,
        log=False,
    ) -> Assignation:
        ass_list_reply: AssignPubReply = await self.awaitaction(
            AssignPub(
                reservation=reservation,
                args=args,
                kwargs=kwargs,
                persist=persist,
                log=log,
            )
        )
        return ass_list_reply

    async def areserve(
        self, node: str, params: ReserveParamsInput = None
    ) -> Reservation:
        action = ReservePub(node=node, params=params)
        resrep: ReservePubReply = await self.awaitaction(action)
        return resrep

    async def aunreserve(self, reservation: str) -> Reservation:
        action = UnreservePub(reservation=reservation)
        unres: UnreservePubReply = await self.awaitaction(action)
        return unres

    async def aunassign(self, assignation: str) -> Reservation:
        action = UnassignPub(assignation=assignation)
        unass: UnassignPubReply = await self.awaitaction(action)
        return unass

    async def alist_assignations(
        self, exclude: Optional[AssignationStatus] = None
    ) -> List[Assignation]:
        action = AssignList(exclude=exclude)
        ass_list_reply: AssingListReply = await self.awaitaction(action)
        return ass_list_reply.assignations

    async def adisconnect(self):
        self._connection_task.cancel()

        try:
            await self._connection_task
        except asyncio.CancelledError:
            pass

    async def __aexit__(self, *args, **kwargs):
        if self._connection_task:
            await self.adisconnect()

    class Config:
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True
