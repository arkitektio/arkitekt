import asyncio
from arkitekt.config import TransportProtocol
from arkitekt.messages.base import MessageModel
from arkitekt.transport.registry import (
    TransportRegistry,
    get_current_transport_registry,
)
from arkitekt.transport.base import Transport
from arkitekt.ward import ArkitektWard
from herre.herre import Herre, get_current_herre
from herre.wards.registry import get_ward_registry
from arkitekt.legacy.utils import *
from arkitekt.registry import set_current_rpc
from koil.koil import Koil, get_current_koil
from fakts import Fakts, get_current_fakts, Config

try:
    from rich.traceback import install

    install()
except:
    pass

import logging

logger = logging.getLogger(__name__)


class PostmanConfig(Config):
    type: TransportProtocol
    kwargs: dict

    class Config:
        group = "arkitekt.postman"


class Postman:
    def __init__(
        self,
        *args,
        auto_login=True,
        auto_connect=True,
        loop=None,
        register=True,
        herre: Herre = None,
        koil: Koil = None,
        fakts: Fakts = None,
        transport_registry: TransportRegistry = None,
        **kwargs,
    ) -> None:

        self.auto_login = auto_login
        self.auto_connect = auto_connect
        self.transport: Transport = None
        self.herre = herre or get_current_herre()
        self.fakts = fakts or get_current_fakts()
        self.ward: ArkitektWard = get_ward_registry().get_ward_instance("arkitekt")
        self.transport_registry = transport_registry or get_current_transport_registry()

        self.connected = False
        self.queues = {}

        if register:
            set_current_rpc(self)

        super().__init__(*args, **kwargs)

    async def adisconnect(self):
        await self.ward.adisconnect()
        await self.transport.adisconnect()
        logger.info(f"Successfully disconnected Postman {self}")

    async def broadcast(self, message: MessageModel):
        if message.meta.reference in self.queues:
            logger.info(f"RPC Message Received")
            await self.queues[message.meta.reference].put(message)
        else:
            logger.error(f"Message without a reply channel {message}")

    async def stream_replies_to_queue(self, message: MessageModel):
        """Creates a queue for this referenced message
        and forwards every message on a reply channel to the return queue

        Args:
            message (MessageModel): [description]

        Returns:
            asyncio.Queue: The Reply Queue
        """
        reply_channel = message.meta.reference
        reply_queue = asyncio.Queue()
        self.queues[reply_channel] = reply_queue
        await self.transport.forward(message)
        return reply_queue

    async def forward(self, message: MessageModel):
        await self.transport.forward(message)

    async def aconnect(self):
        if not self.fakts.loaded:
            await self.fakts.aload()

        if not self.herre.logged_in:
            await self.herre.alogin()

        if not self.ward.connected:
            assert (
                self.auto_connect
            ), "We have not connected to Arkitekt before and autoconnect was set to false. Please connect a ward before or set auto_connect to True"
            await self.ward.aconnect()

        self.config = await PostmanConfig.from_fakts(fakts=self.fakts)
        self.transcript = self.ward.transcript
        self.transport = self.transport_registry.get_postman_transport_for_protocol(
            self.config.type
        )(self.config.kwargs, broadcast=self.broadcast)

        await self.transport.aconnect()
        self.connected = True

    async def __aenter__(self):
        await self.aconnect()
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.adisconnect()
