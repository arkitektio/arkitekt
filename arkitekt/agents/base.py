from arkitekt.monitor.monitor import Monitor
from arkitekt.actors.base import Actor
from arkitekt.messages.postman.unprovide.bounced_unprovide import BouncedUnprovideMessage
from arkitekt.messages.postman.provide.bounced_provide import BouncedProvideMessage
from arkitekt.messages.postman.log import LogLevel
from arkitekt.messages.postman.reserve.bounced_reserve import BouncedReserveMessage
from arkitekt.transport.base import Transport
from arkitekt.messages.base import MessageDataModel
import asyncio
from herre.loop import loopify
from typing import Callable, Dict, List, Tuple, Type
from arkitekt.transport.websocket import WebsocketTransport
from arkitekt.actors.actify import actify, define
from arkitekt.schema.node import Node
from arkitekt.schema.template import Template
from arkitekt.ward import ArkitektWard
from arkitekt.messages import ProvideLogMessage, ProvideCriticalMessage
from arkitekt.schema.negotiation import PostmanProtocol, Transcript
from herre.wards.registry import get_ward_registry
from herre.wards.base import WardException
from herre.auth import get_current_herre
from arkitekt.legacy.utils import *
from arkitekt.registry import set_current_agent

try:
    from rich.traceback import install
    install()
except:
    pass
import logging


logger = logging.getLogger(__name__)



class TemplateParams(dict):
    pass


async def parse_params(params: dict) -> TemplateParams:
    return TemplateParams(**params)


class AgentException(Exception):
    pass


    
class Agent():

    def __init__(self, auto_login=True, auto_connect=True, loop=None, register=True,  with_monitor=False, **kwargs) -> None:
        self.auto_login = auto_login
        self.auto_connect = auto_connect

        self.herre = get_current_herre(**kwargs) 
        self.loop = self.herre.loop
        
        self.ward: ArkitektWard = get_ward_registry().get_ward_instance("arkitekt")
        self.monitor = Monitor("Agent") if with_monitor else None
        self.panel = self.monitor.create_agent_panel(self) if self.monitor else None

        self.message_queue = asyncio.Queue()
        self._connected = False
        self.transport: Transport = None

        if register:
            set_current_agent(self)


        super().__init__()


    @property
    def connected(self):
        """Is this client connected

        Returns:
            [type]: [description]
        """
        return self._connected

    async def disconnect(self):
        await self.ward.disconnect()


    async def broadcast(self, message: MessageDataModel):
        raise NotImplementedError("Please Overwrite")

        
        
    async def connect(self):
        assert self.herre.logged_in, "Herre is not logged in and auto_login was set to false. Please login with Herre first!"

        if not self.ward.connected:
            assert self.auto_connect, "We have not connected to Arkitekt before and autoconnect was set to false. Please connect a ward before or set auto_connect to True"
            await self.ward._connect()


        self.transcript = self.ward.transcript

        # Setup Postman
        agent_type = "WEBSOCKET"

        if agent_type == PostmanProtocol.WEBSOCKET:
            self.transport = WebsocketTransport(broadcast=self.broadcast, route="agent")
        
        self._connected = True

        if self.monitor: self.monitor.__enter__()




    async def aprovide(self):
        """Provide

        Provide takes registered function updates their definition, syncs up with arkitekt and makes them discoverable on arkitekt.
        It then connects as a provider to arkitekt and waits for (already registered) provisions and runs in an infinite providing
        loop.

        Raises:
            ProviderException: [description]
            ProviderException: [description]
        """
        raise NotImplementedError("Please Overwrite")


    def provide(self, as_task=False):
        assert self.herre.logged_in, "Herre is not logged in and auto_login was set to false. Please login with Herre first!"
        return loopify(self.aprovide(), as_task=as_task)



    async def __aenter__(self):
        await self.connect()
        return self


            
    async def __aexit__(self, *args, **kwargs):
        await self.disconnect()
