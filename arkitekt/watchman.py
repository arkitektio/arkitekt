import json
import logging
from typing import Callable, Literal
import asyncio
from pydantic import BaseModel
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError
from arkitekt.api.schema import ReservationStatus
from koil import koil

logger = logging.getLogger(__name__)


class ReserveTransition(BaseModel):
    type: Literal["reserve_transition"]
    reference: str
    status: ReservationStatus


class RetriesExceeded(Exception):
    pass


class WatchmanMessage(BaseModel):
    data: ReserveTransition


class Watchman:
    def __init__(
        self,
        unique_id: str = None,
        token_loader: Callable[[], str] = None,
        ws_url: str = "ws://localhost:8090/watchman/",
        max_retries: int = 3,
        time_between_retries: int = 5,
        **kwargs,
    ) -> None:
        self.token_loader = token_loader
        self.ws_url = ws_url
        self.unique_id = unique_id
        self.max_retires = max_retries
        self.time_between_retries = time_between_retries

    async def abroadcast(self, message):
        print(message)

    async def aconnect(self):
        self.send_queue = asyncio.Queue()
        await self.websocket_loop()

    async def adisconnect(self):
        self.connection_task.cancel()

        try:
            await self.connection_task
        except asyncio.CancelledError:
            logger.info(f"Websocket Transport {self} succesfully disconnected")

    async def websocket_loop(self, retry=0):
        send_task = None
        receive_task = None
        print("hallo")
        try:
            try:

                token = await self.token_loader()
                print(f"{self.ws_url}?token={token}&uuid={self.unique_id}")
                async with websockets.connect(
                    f"{self.ws_url}?token={token}&uuid={self.unique_id}"
                ) as client:
                    print("asdasdasd")
                    send_task = asyncio.create_task(self.sending(client))
                    receive_task = asyncio.create_task(self.receiving(client))

                    self.connection_alive = True
                    self.connection_dead = False
                    done, pending = await asyncio.wait(
                        [send_task, receive_task],
                        return_when=asyncio.FIRST_EXCEPTION,
                    )
                    self.connection_alive = True
                    print("nananana")

                    for task in pending:
                        task.cancel()

                    for task in done:
                        raise task.exception()

            except ConnectionClosedError as e:
                print(e)
                if retry > self.max_retires:
                    raise RetriesExceeded("Exceeded Number of Retries") from e

                print(e)
                await asyncio.sleep(self.time_between_retries)
                await self.websocket_loop(retry=retry + 1)

            except Exception as e:
                print(e)

        except asyncio.CancelledError as e:
            logger.info("Got Canceleld")
            if send_task and receive_task:
                send_task.cancel()
                receive_task.cancel()

            cancellation = await asyncio.gather(
                send_task, receive_task, return_exceptions=True
            )
            raise e

        except Exception as e:
            print(e)
            raise e

    async def sending(self, client):
        try:
            while True:
                message = await self.send_queue.get()
                logger.debug("Postman Websocket: >>>>>> " + message)
                await client.send(message)
                self.send_queue.task_done()
        except asyncio.CancelledError as e:
            logger.debug("Sending Task sucessfully Cancelled")

    async def receiving(self, client):
        try:
            async for message in client:
                print("Nananna")
                logger.debug("Postman Websocket: <<<<<<< " + message)
                message = WatchmanMessage(json.loads(message))
                await self.broadcast(message)

        except asyncio.CancelledError as e:
            logger.debug("Receiving Task sucessfully Cancelled")

    def connect(self):
        return koil(self.aconnect(), as_task=True)
