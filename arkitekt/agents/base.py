from abc import abstractmethod
from arkitekt.actors.base import Actor
from arkitekt.config import TransportProtocol
from arkitekt.messages.postman.assign.bounced_forwarded_assign import (
    BouncedForwardedAssignMessage,
)
from arkitekt.messages.postman.unassign.bounced_forwarded_unassign import (
    BouncedForwardedUnassignMessage,
)
from arkitekt.monitor.monitor import Monitor
from arkitekt.messages.postman.unprovide.bounced_unprovide import (
    BouncedUnprovideMessage,
)
from arkitekt.messages.postman.provide.bounced_provide import BouncedProvideMessage
from arkitekt.messages.postman.log import LogLevel
from arkitekt.messages.postman.reserve.bounced_reserve import BouncedReserveMessage
from arkitekt.transport.agent.base import AgentTransport
from arkitekt.transport.base import Transport
from arkitekt.messages.base import MessageDataModel, MessageModel
import asyncio
from typing import Callable, Dict, List, Tuple, Type
from arkitekt.transport.registry import (
    TransportRegistry,
    get_current_transport_registry,
)
from arkitekt.schema.node import Node
from arkitekt.schema.template import Template
from arkitekt.ward import ArkitektConfig, ArkitektWard
from arkitekt.messages import ProvideLogMessage, ProvideCriticalMessage
from herre.console.context import get_current_console
from herre.herre import Herre, get_current_herre
from herre.wards.registry import get_ward_registry
from herre.wards.base import WardException
from arkitekt.legacy.utils import *
from arkitekt.registry import set_current_agent
from koil.koil import Koil, get_current_koil
from koil.loop import koil
from fakts import Fakts, get_current_fakts, Config

try:
    from rich.traceback import install

    install()
except:
    pass
import logging


logger = logging.getLogger(__name__)


class AgentException(Exception):
    pass


class AgentConfig(Config):
    type: TransportProtocol = TransportProtocol.WEBSOCKET
    debug: bool = False
    kwargs: dict = {}

    class Config:
        group = "arkitekt.agent"


class Agent:
    def __init__(
        self,
        *args,
        auto_login=True,
        auto_connect=True,
        loop=None,
        register=True,
        with_monitor=False,
        herre: Herre = None,
        koil: Koil = None,
        fakts: Fakts = None,
        config: AgentConfig = None,
        transport_registry: TransportRegistry = None,
        strict=False,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.auto_login = auto_login
        self.auto_connect = auto_connect
        self.strict = strict
        self.config = config
        self.herre = herre or get_current_herre()
        self.fakts = fakts or get_current_fakts()

        self.ward: ArkitektWard = get_ward_registry().get_ward_instance("arkitekt")
        self.monitor = Monitor("Agent") if with_monitor else None
        self.panel = self.monitor.create_agent_panel(self) if self.monitor else None
        self.message_queue = asyncio.Queue()
        self.transport: AgentTransport = None
        self.transport_registry = transport_registry or get_current_transport_registry()

        self.runningActors: Dict[str, Actor] = {}
        self.runningTasks: Dict[str, asyncio.Task] = {}

        if register:
            set_current_agent(self)

    @abstractmethod
    async def handle_bounced_provide(self, bounced_provide: BouncedProvideMessage):
        raise NotImplementedError()

    @abstractmethod
    async def handle_bounced_unprovide(
        self, bounced_unprovide: BouncedUnprovideMessage
    ):
        raise NotImplementedError()

    @abstractmethod
    async def handle_bounced_assign(
        self, bounced_assign: BouncedForwardedAssignMessage
    ):
        raise NotImplementedError()

    @abstractmethod
    async def handle_bounced_unassign(
        self, bounced_unassign: BouncedForwardedUnassignMessage
    ):
        raise NotImplementedError()

    async def broadcast(self, message: MessageModel):

        logger.info(f"Provider: [green] Received message {message}")
        try:
            if isinstance(message, BouncedProvideMessage):
                logger.info("Received Provide Request")
                assert (
                    message.data.template is not None
                ), "Received Provision that had no Template???"
                await self.handle_bounced_provide(message)

            elif isinstance(message, BouncedUnprovideMessage):
                logger.info("Received Unprovide Request")
                assert (
                    message.data.provision is not None
                ), "Received Unprovision that had no Provision???"
                await self.handle_bounced_unprovide(message)

            elif isinstance(message, BouncedForwardedAssignMessage):
                logger.info("Received Assing Request")
                assert (
                    message.data.provision is not None
                ), "Received Assignment that had no Provision???"
                await self.handle_bounced_assign(message)

            elif isinstance(message, BouncedForwardedUnassignMessage):
                logger.info("Received Unassign Request")
                assert (
                    message.data.provision is not None
                ), "Received Assignment that had no Provision???"
                await self.handle_bounced_unassign(message)

            else:
                logger.info(f"Provider: [red] Received unknown message {message}")
        except Exception as e:
            logger.exception(e)

    async def on_transport_connected(self):
        return None

    async def on_transport_about_to_connect(self):
        return None

    async def on_transport_about_to_disconnect(self):
        return None

    async def aprovide(self):
        caused_ward_connect = False
        try:
            if not self.fakts.loaded:
                await self.fakts.aload()

            if not self.herre.logged_in:
                await self.herre.alogin()

            if not self.ward.connected:
                assert (
                    self.auto_connect
                ), "We have not connected to Arkitekt before and autoconnect was set to false. Please connect a ward before or set auto_connect to True"
                await self.ward.aconnect()
                caused_ward_connect = True

            if not self.config:
                self.config = await AgentConfig.from_fakts(fakts=self.fakts)

            self.transcript = self.ward.transcript
            self.transport = self.transport_registry.get_agent_transport_for_protocol(
                self.config.type
            )(self.config.kwargs, broadcast=self.broadcast)

            await self.on_transport_about_to_connect()
            await self.transport.aconnect()

        except asyncio.CancelledError as e:

            tasks = [task for key, task in self.runningTasks.items()]
            for task in tasks:
                logger.info(f"Cancelling Actor Task: {task}")
                task.cancel()

            exceptions = await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("All Actors Done. Bye Bye!")

            if self.transport:
                await self.on_transport_about_to_disconnect()
                await self.transport.adisconnect()
            if caused_ward_connect:
                await self.ward.adisconnect()

            raise e

        except Exception as e:
            logger.exception(e)
            raise e

    def provide(self, **kwargs):

        with get_current_console().status("Providing"):
            return koil(self.aprovide(), **kwargs)
