from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, Union
import websockets
from arkitekt.agents.transport.base import AgentTransport
import asyncio
import json
from arkitekt.agents.transport.errors import (
    AgentTransportException,
    AssignationListDeniedError,
    ProvisionListDeniedError,
)
from arkitekt.agents.transport.protocols.agent_json import *
import logging
from websockets.exceptions import (
    ConnectionClosedError,
)

logger = logging.getLogger(__name__)


async def token_loader():
    raise NotImplementedError(
        "Websocket transport does need a defined token_loader on Connection"
    )


class CorrectableConnectionFail(AgentTransportException):
    pass


class DefiniteConnectionFail(AgentTransportException):
    pass


@dataclass
class WebsocketAgentTransport(AgentTransport):
    ws_url: str
    instance_id: Optional[str]
    token_loader: Callable[[], Awaitable[str]]
    abroadcast: Optional[
        Callable[[Union[Assignation, Provision]], Awaitable[None]]
    ] = None
    max_retries = 5
    time_between_retries = 5
    allow_reconnect = True

    _futures: Dict[str, asyncio.Future] = field(default_factory=dict)
    _connected = False
    _healthy = False
    _send_queue: Optional[asyncio.Queue] = None
    _connection_task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        assert self.abroadcast is not None, "Broadcast must be defined"
        self._send_queue = asyncio.Queue()
        self._connection_task = asyncio.create_task(self.websocket_loop())
        self._connected = True

    async def websocket_loop(self, retry=0):
        send_task = None
        receive_task = None
        try:
            try:
                token = await self.token_loader()

                async with websockets.connect(
                    f"{self.ws_url}?token={token}&instance_id={self.instance_id}"
                ) as client:

                    logger.info("Postman on Websockets connected")

                    send_task = asyncio.create_task(self.sending(client))
                    receive_task = asyncio.create_task(self.receiving(client))

                    self._healthy = True
                    done, pending = await asyncio.wait(
                        [send_task, receive_task],
                        return_when=asyncio.FIRST_EXCEPTION,
                    )
                    self._healthy = False

                    for task in pending:
                        task.cancel()

                    for task in done:
                        raise task.exception()

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
            await self.websocket_loop(retry=retry + 1)

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
            print(json_dict)

            # State Layer
            if type == AgentSubMessageTypes.ASSIGN:
                await self.broadcast(AssignSubMessage(**json_dict))

            if type == AgentSubMessageTypes.PROVIDE:
                await self.broadcast(ProvideSubMessage(**json_dict))

            if type == AgentMessageTypes.LIST_ASSIGNATIONS_REPLY:
                self._futures[id].set_result(AssignationsListReply(**json_dict))
            if type == AgentMessageTypes.LIST_ASSIGNATIONS_DENIED:
                self._futures[id].set_exception(
                    AssignationListDeniedError(json_dict["error"])
                )

            if type == AgentMessageTypes.LIST_PROVISIONS_REPLY:
                self._futures[id].set_result(ProvisionListReply(**json_dict))
            if type == AgentMessageTypes.LIST_PROVISIONS_DENIED:
                self._futures[id].set_exception(
                    ProvisionListDeniedError(json_dict["error"])
                )

        else:
            print(f"Error {json_dict}")

    async def awaitaction(self, action: JSONMessage):
        assert self._connected, "Websocket is not connected"
        if action.id in self._futures:
            raise ValueError("Action already has a future")

        future = asyncio.Future()
        self._futures[action.id] = future
        await self._send_queue.put(action.json())
        return await future

    async def delayaction(self, action: JSONMessage):
        assert self._connected, "Websocket is not connected"
        await self._send_queue.put(action.json())

    async def list_provisions(
        self, exclude: Optional[ProvisionStatus] = None
    ) -> List[Provision]:
        action = ProvisionList(exclude=exclude)
        prov_list_reply: ProvisionListReply = await self.awaitaction(action)
        return prov_list_reply.provisions

    async def change_provision(
        self,
        id: str,
        status: ProvisionStatus = None,
        message: str = None,
        mode: ProvisionMode = None,
    ):
        action = ProvisionChangedMessage(
            provision=id, status=status, message=message, mode=mode
        )
        await self.delayaction(action)

    async def change_assignation(
        self,
        id: str,
        status: AssignationStatus = None,
        message: str = None,
        returns: List[Any] = None,
    ):
        action = AssignationChangedMessage(
            assignation=id, status=status, message=message, returns=returns
        )
        await self.delayaction(action)

    async def list_assignations(
        self, exclude: Optional[AssignationStatus] = None
    ) -> List[Assignation]:
        action = AssignationsList(exclude=exclude)
        ass_list_reply: AssignationsListReply = await self.awaitaction(action)
        return ass_list_reply.assignations

    async def __aexit__(self, *args, **kwargs):
        self._connection_task.cancel()
        self._connected = False

        try:
            await self._connection_task
        except asyncio.CancelledError:
            pass
