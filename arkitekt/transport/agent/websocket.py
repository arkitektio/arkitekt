from pydantic.main import BaseModel
from websockets.exceptions import ConnectionClosedError
from arkitekt.config import TransportProtocol
from arkitekt.transport.agent.base import AgentTransportConfig
from arkitekt.transport.base import Transport, TransportConfig
from arkitekt.messages.utils import expandToMessage
from arkitekt.messages.base import MessageMetaExtensionsModel, MessageModel
from arkitekt.transport.registry import register_agent_transport
from herre.herre import get_current_herre
from enum import Enum
import websockets
import json
import asyncio
from arkitekt.legacy.utils import create_task
import logging

logger = logging.getLogger(__name__)


class AgentWebsocketCodes(int, Enum):
    ALREADY_CONNECTED_IDENTIFER = 4001


class WebsocketAgentTransportConfig(AgentTransportConfig):
    host: str
    port: int
    secure: bool = False

    @property
    def protocol(self):
        return "wss" if self.secure else "ws"


class ConnectionFailedError(Exception):
    pass


class CorrectableConnectionFail(ConnectionFailedError):
    pass


class DefiniteConnectionFail(ConnectionFailedError):
    pass


@register_agent_transport(TransportProtocol.WEBSOCKET)
class WebsocketAgentTransport(Transport):
    configClass = WebsocketAgentTransportConfig
    config: WebsocketAgentTransportConfig

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.send_queue = None
        self.retries = 5
        self.time_between_retries = 5
        self.connection_alive = False
        self.connection_dead = False

    async def aconnect(self):
        if not self.herre.logged_in:
            await self.herre.alogin()

        self.send_queue = asyncio.Queue()
        await self.websocket_loop()

    async def adisconnect(self):
        logger.info(f"Websocket Transport {self} succesfully disconnected")

    async def websocket_loop(self, retry=0):
        send_task = None
        receive_task = None
        try:
            try:
                async with websockets.connect(
                    f"{self.config.protocol}://{self.config.host}:{self.config.port}/agent/?token={self.herre.state.access_token}&identifier={self.config.identifier}"
                ) as client:

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

                    for task in done:
                        raise task.exception()

            except ConnectionClosedError as e:
                logger.exception(e)
                if e.code == AgentWebsocketCodes.ALREADY_CONNECTED_IDENTIFER:
                    raise DefiniteConnectionFail(
                        f"Another agent was already connected on {self.config.identifier}! Please set a different identifier if you want to connect!"
                    ) from e

                raise CorrectableConnectionFail from e

            except Exception as e:
                logger.warning(
                    "THIS EXCEPTION HAS NO RETRY STRATEGY... TRYING TO RETRY??"
                )
                raise CorrectableConnectionFail from e

        except CorrectableConnectionFail as e:
            logger.info(f"Trying to Recover from Exception {e}")
            if retry > self.retries:
                raise DefiniteConnectionFail("Exceeded Number of Retries")
            await asyncio.sleep(self.time_between_retries)
            logger.info(f"Retrying to connect")
            await self.websocket_loop(retry=retry + 1)

        except DefiniteConnectionFail as e:
            self.connection_dead = False
            raise e

        except asyncio.CancelledError as e:
            logger.info("Got Canceleld")
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
                message = await self.send_queue.get()
                logger.debug("Agent Websocket: >>>>>> " + message)
                await client.send(message)
                self.send_queue.task_done()
        except asyncio.CancelledError as e:
            logger.debug("Sending Task sucessfully Cancelled")

    async def receiving(self, client):
        try:
            async for message in client:
                logger.debug("Agent Websocket: <<<<<<< " + message)
                message = expandToMessage(json.loads(message))
                await self.broadcast(message)
        except asyncio.CancelledError as e:
            logger.debug("Receiving Task sucessfully Cancelled")

    async def forward(self, message: MessageModel):
        assert (
            not self.connection_dead
        ), "Connection is definetly dead. Retries have been exceeded. Error"
        await self.send_queue.put(json.dumps(message.dict()))
