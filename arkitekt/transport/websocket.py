from arkitekt.transport.base import Transport, TransportConfig
from arkitekt.messages.utils import expandToMessage
from arkitekt.messages.base import MessageMetaExtensionsModel, MessageModel
from herre.config.base import BaseConfig
from enum import Enum
import websockets
import json
import asyncio
from arkitekt.legacy.utils import create_task
import logging

logger = logging.getLogger(__name__)


class WebsocketTransportConfig(TransportConfig):
    host: str
    port: int
    secure: bool = False
    route: str

    @property
    def protocol(self):
        return "wss" if self.secure else "ws"


class ConnectionFailedError(Exception):
    pass


class WebsocketTransport(Transport):


    def __init__(self, config = None, broadcast=None, **kwargs) -> None:

        super().__init__(broadcast)
        self.config = config or WebsocketTransportConfig.from_file("bergen.yaml", **kwargs)
        self.retries = 5
        self.time_between_retries = 5
        self.connection_alive = False
        self.connection_dead = False


    async def connect(self):
        assert self.herre.logged_in, "Needs to be logged in order to connect"

        self.send_queue = asyncio.Queue()
        self.connection =  create_task(self.connection_task())

    async def connection_task(self, retry=0):

        assert retry < self.retries, "Exceeded number of retries! Postman is disconnected"
        try:
            try:
                async with websockets.connect(f"{self.config.protocol}://{self.config.host}:{self.config.port}/{self.config.route}/?token={self.herre.grant.access_token}") as client:

                    send_task = create_task(self.sending(client))
                    receive_task = create_task(self.receiving(client))

                    self.connection_alive = True
                    self.connection_dead = False
                    done, pending = await asyncio.wait(
                        [send_task, receive_task],
                        return_when=asyncio.FIRST_EXCEPTION,
                    )
                    self.connection_alive = True

                    for task in pending:
                        task.cancel()

                    raise ConnectionFailedError("Connection failed")

            except Exception as e:
                raise ConnectionFailedError from e

        except ConnectionFailedError as e:
            logger.error("Connection failed Retrying")
            await asyncio.sleep(self.time_between_retries)
            await self.connection_task(retry=retry + 1)

        except AssertionError as e:
            logger.error("Connection failed Definetly. Postman will fail on next call!")
            self.connection_dead = False

        except asyncio.CancelledError as e:
            logger.info("Got Canceleld")


    async def sending(self, client):
        while True:
            message = await self.send_queue.get()
            logger.info(">>>>>> " + message)
            await client.send(message)
            self.send_queue.task_done()


    async def receiving(self, client):
        async for message in client:
            logger.info("<<<<<<< " + message)
            message = expandToMessage(json.loads(message))
            await self.broadcast(message)


    async def forward(self, message: MessageModel):
        assert not self.connection_dead, "Connection is definetly dead. Retries have been exceeded. Error"
        await self.send_queue.put(json.dumps(message.dict()))
        


    