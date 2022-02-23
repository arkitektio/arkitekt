import asyncio
import json

import websockets
from arkitekt.postmans.transport.base import PostmanTransport
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union
from arkitekt.messages import Assignation, Reservation, Unassignation, Unreservation
from arkitekt.postmans.transport.errors import (
    AssignDeniedError,
    AssignationListDeniedError,
    ReservationListDeniedError,
    ReserveDeniedError,
    UnassignDeniedError,
    UnreserveDeniedError,
)
from .protocols.postman_json import *


async def token_loader():
    raise NotImplementedError(
        "Websocket transport does need a defined token_loader on Connection"
    )


class WebsocketPostmanTransport(PostmanTransport):
    def __init__(
        self,
        *args,
        ws_url="ws://localhost:8090/watchi/",
        instance_id=None,
        token_loader=token_loader,
        abroadcast: Callable[[Union[Assignation, Reservation]], Awaitable[None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.retries = 5
        self.time_between_retries = 5
        self.connection_alive = False
        self.connection_dead = False
        self.token_loader = token_loader
        self.ws_url = ws_url
        self.instance_id = instance_id
        self.futures = {}
        self.abroadcast = abroadcast

    async def aconnect(self):
        assert (
            self.abroadcast is not None
        ), "Broadcast must be defined (either overwrite abroadcast or pass this in constructor of transport)"
        self.send_queue = asyncio.Queue()
        self.connection_task = asyncio.create_task(self.websocket_loop())

    async def websocket_loop(self, retry=0):
        send_task = None
        receive_task = None
        try:
            token = await self.token_loader()
            assert self.instance_id, "Needs an instance id"
            async with websockets.connect(
                f"{self.ws_url}?token={token}&instance_id={self.instance_id}"
            ) as client:

                send_task = asyncio.create_task(self.sending(client))
                receive_task = asyncio.create_task(self.receiving(client))

                self.connection_alive = True
                self.connection_dead = False
                done, pending = await asyncio.wait(
                    [send_task, receive_task],
                    return_when=asyncio.FIRST_EXCEPTION,
                )
                self.connection_alive = True

                for task in pending:
                    task.cancel()

                for task in done:
                    raise task.exception()

        except Exception as e:
            print("Error on Websockets", e)
            raise e

    async def sending(self, client):
        try:
            while True:
                message = await self.send_queue.get()
                await client.send(message)
                self.send_queue.task_done()
        except asyncio.CancelledError as e:
            print("Sending Task sucessfully Cancelled")

    async def receiving(self, client):
        try:
            async for message in client:
                await self.receive(message)
        except asyncio.CancelledError as e:
            print("Receiving Task sucessfully Cancelled")

    async def receive(self, message):
        json_dict = json.loads(message)
        if "type" in json_dict:
            type = json_dict["type"]
            id = json_dict["id"]
            print(json_dict)

            # State Layer
            if type == PostmanSubMessageTypes.ASSIGN_UPDATE:
                await self.abroadcast(AssignSubUpdate(**json_dict))

            if type == PostmanSubMessageTypes.RESERVE_UPDATE:
                await self.abroadcast(ReserveSubUpdate(**json_dict))

            if type == PostmanMessageTypes.LIST_ASSIGNATION_REPLY:
                self.futures[id].set_result(AssingListReply(**json_dict))
            if type == PostmanMessageTypes.LIST_ASSIGNATION_DENIED:
                self.futures[id].set_exception(
                    AssignationListDeniedError(json_dict["error"])
                )

            if type == PostmanMessageTypes.LIST_RESERVATION_REPLY:
                self.futures[id].set_result(ReserveListReply(**json_dict))
            if type == PostmanMessageTypes.LIST_RESERVATION_DENIED:
                self.futures[id].set_exception(
                    ReservationListDeniedError(json_dict["error"])
                )

            if type == PostmanMessageTypes.ASSIGN_REPLY:
                self.futures[id].set_result(AssignPubReply(**json_dict))
            if type == PostmanMessageTypes.ASSIGN_DENIED:
                self.futures[id].set_exception(AssignDeniedError(json_dict["error"]))

            if type == PostmanMessageTypes.UNASSIGN_REPLY:
                self.futures[id].set_result(UnassignPubReply(**json_dict))
            if type == PostmanMessageTypes.UNASSIGN_DENIED:
                self.futures[id].set_exception(UnassignDeniedError(json_dict["error"]))

            if type == PostmanMessageTypes.RESERVE_REPLY:
                self.futures[id].set_result(ReservePubReply(**json_dict))
            if type == PostmanMessageTypes.RESERVE_DENIED:
                self.futures[id].set_exception(ReserveDeniedError(json_dict["error"]))

            if type == PostmanMessageTypes.UNRESERVE_REPLY:
                self.futures[id].set_result(UnreservePubReply(**json_dict))
            if type == PostmanMessageTypes.UNRESERVE_DENIED:
                self.futures[id].set_exception(UnreserveDeniedError(json_dict["error"]))

        else:
            print(f"Error {json_dict}")

    async def alist_reservations(
        self, exclude: Optional[ReservationStatus] = None
    ) -> List[Reservation]:
        action = ReserveList(exclude=exclude)
        self.futures[str(action.id)] = asyncio.Future()
        await self.send_queue.put(action.json())
        prov_list_reply: ReserveListReply = await self.futures[str(action.id)]
        return prov_list_reply.reservations

    async def aassign(
        self,
        reservation: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        persist=True,
        log=False,
    ) -> Assignation:
        action = AssignPub(
            reservation=reservation, args=args, kwargs=kwargs, persist=persist, log=log
        )
        self.futures[str(action.id)] = asyncio.Future()
        await self.send_queue.put(action.json())
        ass_list_reply: AssignPubReply = await self.futures[str(action.id)]
        return ass_list_reply

    async def areserve(
        self, node: str, params: ReserveParamsInput = None
    ) -> Reservation:
        action = ReservePub(node=node, params=params)
        self.futures[str(action.id)] = asyncio.Future()
        await self.send_queue.put(action.json())
        ass_list_reply: ReserveListReply = await self.futures[str(action.id)]
        return ass_list_reply

    async def aunreserve(self, reservation: str) -> Reservation:
        action = UnreservePub(reservation=reservation)
        self.futures[str(action.id)] = asyncio.Future()
        await self.send_queue.put(action.json())
        unres: UnreservePubReply = await self.futures[str(action.id)]
        return unres

    async def aunassign(self, assignation: str) -> Reservation:
        action = UnassignPub(assignation=assignation)
        self.futures[str(action.id)] = asyncio.Future()
        await self.send_queue.put(action.json())
        unass: UnassignPubReply = await self.futures[str(action.id)]
        return unass

    async def alist_assignations(
        self, exclude: Optional[AssignationStatus] = None
    ) -> List[Assignation]:
        action = AssignList(exclude=exclude)
        self.futures[str(action.id)] = asyncio.Future()
        await self.send_queue.put(action.json())
        ass_list_reply: AssingListReply = await self.futures[str(action.id)]
        return ass_list_reply.assignations

    async def adisconnect(self):
        self.connection_task.cancel()

        try:
            await self.connection_task
        except asyncio.CancelledError:
            pass
