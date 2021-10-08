from abc import abstractmethod
from arkitekt.config import TransportProtocol
from arkitekt.messages.postman.assign.bounced_forwarded_assign import BouncedForwardedAssignMessage
from arkitekt.messages.postman.unassign.bounced_forwarded_unassign import BouncedForwardedUnassignMessage
from arkitekt.monitor.monitor import Monitor
from arkitekt.actors.base import Actor
from arkitekt.messages.postman.unprovide.bounced_unprovide import BouncedUnprovideMessage
from arkitekt.messages.postman.provide.bounced_provide import BouncedProvideMessage
from arkitekt.messages.postman.log import LogLevel
from arkitekt.messages.postman.reserve.bounced_reserve import BouncedReserveMessage
from arkitekt.transport.base import Transport
from arkitekt.messages.base import MessageDataModel, MessageModel
import asyncio
from typing import Callable, Dict, List, Tuple, Type
from arkitekt.transport.registry import TransportRegistry, get_current_transport_registry
from arkitekt.transport.websocket import WebsocketTransport
from arkitekt.actors.actify import actify, define
from arkitekt.schema.node import Node
from arkitekt.schema.template import Template
from arkitekt.ward import ArkitektConfig, ArkitektWard
from arkitekt.messages import ProvideLogMessage, ProvideCriticalMessage
from herre.herre import Herre, get_current_herre
from herre.wards.registry import get_ward_registry
from herre.wards.base import WardException
from arkitekt.legacy.utils import *
from arkitekt.registry import set_current_agent
from koil.koil import Koil, get_current_koil
from koil.loop import koil
import konfik
from konfik.config.base import Config
from konfik.konfik import Konfik, get_current_konfik

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

class AgentConfig(Config):
    type: TransportProtocol = TransportProtocol.WEBSOCKET
    kwargs: dict = {}

    class Config:
        group = "arkitekt.agent"

    
class Agent:

    def __init__(self, *args, auto_login=True, auto_connect=True, loop=None, register=True,  with_monitor=False, herre: Herre = None, koil: Koil = None, konfik: Konfik = None, transport_registry: TransportRegistry= None, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.auto_login = auto_login
        self.auto_connect = auto_connect

        self.herre = herre or get_current_herre() 
        self.koil = koil or get_current_koil()
        self.konfik = konfik or get_current_konfik()
        self.loop = self.koil.loop
        
        self.ward: ArkitektWard = get_ward_registry().get_ward_instance("arkitekt")
        self.monitor = Monitor("Agent") if with_monitor else None
        self.panel = self.monitor.create_agent_panel(self) if self.monitor else None
        self.message_queue = asyncio.Queue()
        self.transport: Transport = None
        self.transport_registry = transport_registry or get_current_transport_registry()


        self.potentialNodes: List[Tuple[Node, Callable]] = []
        self.potentialTemplates: List[Tuple[Node, Callable]] = []
        self.approvedTemplates: List[Tuple[Template, Callable]] = []
        self.approvedActors: Dict[str, Type[Actor]] = {}

        # Running Actors indexed by their ID
        self.runningActors: Dict[str, Actor] = {}
        self.runningTasks: Dict[str, asyncio.Task] = {}


        if register:
            set_current_agent(self)


    @abstractmethod
    async def handle_bounced_provide(self, bounced_provide: BouncedProvideMessage):
        raise NotImplementedError()

    @abstractmethod
    async def handle_bounced_unprovide(self, bounced_unprovide: BouncedUnprovideMessage):
        raise NotImplementedError()


    @abstractmethod
    async def handle_bounced_assign(self, bounced_assign: BouncedForwardedAssignMessage):
        raise NotImplementedError()

    @abstractmethod
    async def handle_bounced_unassign(self, bounced_unassign: BouncedForwardedUnassignMessage):
        raise NotImplementedError()


    async def broadcast(self, message: MessageModel):

        logger.info(f"Provider: [green] Received message {message}")
        try:
            if isinstance(message, BouncedProvideMessage):
                logger.info("Received Provide Request")
                assert message.data.template is not None, "Received Provision that had no Template???"
                await self.handle_bounced_provide(message)

            elif isinstance(message, BouncedUnprovideMessage):
                logger.info("Received Unprovide Request")
                assert message.data.provision is not None, "Received Unprovision that had no Provision???"
                await self.handle_bounced_unprovide(message)

            elif isinstance(message, BouncedForwardedAssignMessage):
                logger.info("Received Assing Request")
                assert message.data.provision is not None, "Received Assignment that had no Provision???"
                await self.handle_bounced_assign(message)

            elif isinstance(message, BouncedForwardedUnassignMessage):
                logger.info("Received Unassign Request")
                assert message.data.provision is not None, "Received Assignment that had no Provision???"
                await self.handle_bounced_unassign(message)

            else: 
                logger.info(f"Provider: [red] Received unknown message {message}")
        except Exception as e:
            logger.exception(e)


    async def aprovide(self):
        caused_ward_connect = False
        try:
            if not self.konfik.load_group:
                await self.konfik.aload()

            if not self.herre.logged_in:
                await self.herre.alogin()

            if not self.ward.connected:
                assert self.auto_connect, "We have not connected to Arkitekt before and autoconnect was set to false. Please connect a ward before or set auto_connect to True"
                await self.ward.aconnect()
                caused_ward_connect = True


            print("Receached Herre")

            self.config = AgentConfig.from_konfik(self.konfik)
            print(self.config)
            self.transcript = self.ward.transcript
            self.transport = self.transport_registry.get_transport_for_protocol(self.config.type)(self.config.kwargs, broadcast=self.broadcast)




            if self.potentialNodes:
                for defined_node, defined_actor, params in self.potentialNodes:
                    # Defined Node are nodes that are not yet reflected on arkitekt (i.e they dont have an instance
                    # id so we are trying to send them to arkitekt)
                    try:
                        arkitekt_node = await Node.asyncs.create(**defined_node.dict(as_input=True))
                        self.potentialTemplates.append((arkitekt_node, defined_actor, params))   
                    except WardException as e:
                        raise AgentException(f"Couldn't create Node for defintion {defined_node}") from e

            if self.potentialTemplates:
                # This is an arkitekt Node and we can generate potential Templates
                for arkitekt_node, defined_actor, params in self.potentialTemplates:
                    try:
                        params = await parse_params(params) # Parse the parameters for template creation
                        arkitekt_template = await Template.asyncs.create(node=arkitekt_node, params=params)
                        self.approvedTemplates.append((arkitekt_template, defined_actor, params))  
                    except WardException as e:
                        raise AgentException(f"Couldn't approve template for node {arkitekt_node}") from e


            if self.approvedTemplates:
                for arkitekt_template, defined_actor, params in self.approvedTemplates:
                    self.approvedActors[arkitekt_template.id] = defined_actor
                    if self.panel: self.panel.add_to_actor_map(arkitekt_template, defined_actor) 
            
            
            await self.transport.aconnect()


            print(f"Hosting {self.approvedTemplates}")

            while True:
                await asyncio.sleep(1)
                print("Providing....")

        except asyncio.CancelledError as e:
            print("Cancelled Here")

            if self.transport: await self.transport.adisconnect()
            if caused_ward_connect: await self.ward.adisconnect()
            raise e

        except Exception as e:
            logger.exception(e)
            raise e


    def provide(self, **kwargs):
        return koil(self.aprovide(), **kwargs)



