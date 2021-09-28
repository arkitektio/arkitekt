import asyncio
from arkitekt.messages.base import MessageModel
from arkitekt.transport.websocket import WebsocketTransport
from arkitekt.transport.base import Transport
from arkitekt.actors.actify import define
from arkitekt.schema.node import Node
from arkitekt.ward import ArkitektWard
from arkitekt.schema.negotiation import PostmanProtocol, Transcript
from herre.wards.registry import get_ward_registry
from herre.auth import get_current_herre
from arkitekt.legacy.utils import *
from arkitekt.registry import set_current_rpc

try:
    from rich.traceback import install
    install()
except:
    pass

import logging

logger = logging.getLogger(__name__)


class RPC():

    def __init__(self, auto_login=True, auto_connect=True, loop=None, register=True, **kwargs) -> None:

        self.auto_login = auto_login
        self.auto_connect = auto_connect
        self.transport: Transport = None
        self.herre = get_current_herre(**kwargs) 
        self.loop = self.herre.loop
        self.ward: ArkitektWard = get_ward_registry().get_ward_instance("arkitekt")
        self.scopes = self.herre.grant.scopes

        self._connected = False
        self.queues = {}

        if register:
            set_current_rpc(self)


        super().__init__(**kwargs)


    @property
    def connected(self):
        """Is this client connected

        Returns:
            [type]: [description]
        """
        return self._connected

    async def disconnect(self):
        await self.ward.disconnect()


    async def broadcast(self, message: MessageModel):
        if message.meta.reference in self.queues:
            logger.info(f"RPC Message Received")
            await self.queues[message.meta.reference].put(message)
        else:
            logger.error(f"Message without a reply channel {message}")


    async def stream_replies_to_queue(self, message: MessageModel):
        """ Creates a queue for this referenced message
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
        
        
    async def connect(self):
        assert self.herre.logged_in, "Herre is not logged in and auto_login was set to false. Please login with Herre first!"

        if not self.ward.connected:
            assert self.auto_connect, "We have not connected to Arkitekt before and autoconnect was set to false. Please connect a ward before or set auto_connect to True"
            await self.ward._connect()


        self.transcript = self.ward.transcript

        # Setup Postman
        postman_type = self.transcript.postman.type

        if postman_type == PostmanProtocol.WEBSOCKET:
            self.transport = WebsocketTransport(**self.transcript.postman.kwargs, broadcast=self.broadcast, route="all")

        await self.transport.connect()
        self._connected = True


    async def __aenter__(self):
        await self.connect()
        return self


            
    async def __aexit__(self, *args, **kwargs):
        await self.disconnect()






