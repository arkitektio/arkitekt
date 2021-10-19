

from arkitekt.agents.app import AppAgent
from arkitekt.agents.qt.actor import QtActor
from herre.herre import get_current_herre
from arkitekt.threadvars import get_current_assign
from qtpy.QtCore import QObject, Signal
from arkitekt.messages.postman.assign.assign_cancelled import AssignCancelledMessage
from arkitekt.messages.postman.unassign.bounced_forwarded_unassign import BouncedForwardedUnassignMessage
from arkitekt.messages.postman.provide.provide_transition import ProvideState, ProvideTransitionMessage
from arkitekt.messages.postman.assign.assign_log import AssignLogMessage
from arkitekt.messages.postman.assign.assign_critical import AssignCriticalMessage
from arkitekt.messages.postman.assign.bounced_forwarded_assign import BouncedForwardedAssignMessage
from arkitekt.messages.postman.assign.bounced_assign import BouncedAssignMessage
from arkitekt.messages.postman.provide.provide_critical import ProvideCriticalMessage
from arkitekt.messages.postman.log import LogLevel
from arkitekt.messages.postman.provide.provide_log import ProvideLogMessage
import asyncio
from herre.wards.base import WardException
from arkitekt.actors.actify import actify, define
from arkitekt.actors.base import Actor
from arkitekt.messages.postman.unprovide.bounced_unprovide import BouncedUnprovideMessage
from arkitekt.messages.base import MessageDataModel, MessageModel
from arkitekt.messages.postman.provide.bounced_provide import BouncedProvideMessage
from arkitekt.schema.template import Template
from arkitekt.schema.node import Node
from arkitekt.packers.transpilers import Transpiler
from typing import Callable, Dict, List, Tuple, Type
from arkitekt.agents.base import Agent, AgentException, parse_params
import logging
from herre.console import get_current_console
import uuid
from koil import get_current_koil

logger = logging.getLogger(__name__)


class AgentSignals(QObject):
    provide = Signal(BouncedProvideMessage)
    unprovide = Signal(BouncedUnprovideMessage)
    provide_transition = Signal(ProvideTransitionMessage)


    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)







class QtAgent(AppAgent, QObject):
    provide_signal = Signal(bool)
    provision_signal = Signal(BouncedProvideMessage)
    unprovision_signal = Signal(BouncedUnprovideMessage)

    ACTOR_PENDING_MESSAGE = "Actor is Pending"

    def __init__(self,*args, strict=False, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.strict = strict
        self.assignFutures = {}
        self.provideFutures = {}
        self.unprovideFutures = {}
        self.appWorkers = {}


    def on_task_done(self, future):
        print(future)

    async def on_bounced_provide(self, message: BouncedProvideMessage):
        self.provision_signal.emit(message)
        if message.data.template in self.templateActorsMap:
            if message.meta.reference in self.templateActorsMap:
                if self.strict: raise AgentException("Already Running Provision Received Again. Right now causing Error. Might be omitted")
                again_provided = ProvideTransitionMessage(data={
                    "message": "Provision was running on this Instance. Probably a freaking race condition",
                    "state": ProvideState.ACTIVE
                    }, meta={"extensions": message.meta.extensions, "reference": message.meta.reference})
                await self.transport.forward(again_provided)
            else:
                actor = self.templateActorsMap[message.data.template]
                self.runningActors[message.meta.reference] = actor
                print("RUnning Actor Here")
                task = self.loop.create_task(actor.arun(message, self))
                task.add_done_callback(self.on_task_done)
                self.runningTasks[message.meta.reference] = task

        else:
            raise AgentException("No approved actors for this template")


    async def on_bounced_unprovide(self, message: BouncedUnprovideMessage):
        if message.data.provision not in self.runningActors: raise AgentException("Already Running Provision Received Again. Right now causing Error. Might be omitted")
        actor = self.runningActors[message.data.provision]
        
        logger.info(f"Cancelling {actor}")
        self.runningTasks[message.data.provision].cancel()
        self.unprovision_signal.emit(message)

    async def on_bounced_assign(self, message: BouncedForwardedAssignMessage):

        if message.data.provision in self.runningActors:
            actor = self.runningActors[message.data.provision]
            await actor.acall(message=message)    
        else:
            if self.strict: raise AgentException("Received Assignment for not running Provision")

    async def on_bounced_unassign(self, message: BouncedForwardedUnassignMessage):

        if message.data.provision in self.runningActors:
            actor = self.runningActors[message.data.provision]
            await actor.acall(message=message)
            
        else:
            if self.strict: raise AgentException("Received Assignment for not running Provision")
            logger.info("We didnt have this assignment, setting Cancellation anyways")
            await self.transport.forward(AssignCancelledMessage(data={
                "canceller": "Fake Cancellation trough Provider"
            }, meta = {
                "reference": message.data.assignation
            }))
                

    def register(self, function_or_node, widgets={}, transpilers: Dict[str, Transpiler] = None, on_provide = None, on_unprovide = None, on_assign = None, timeout=500, **params) -> QtActor:

        # Simple bypass for now
        defined_actor = QtActor(qt_assign=on_assign, qt_on_provide=on_provide, qt_on_unprovide=on_unprovide, loop=self.loop, timeout=timeout, **params)
        
        if isinstance(function_or_node, str):
            self.templatedUnqueriedNodes.append(({"q": function_or_node}, defined_actor, params))
           
        if isinstance(function_or_node, Node):
            self.templatedNodes.append((function_or_node, defined_actor, params))

        else:
            defined_node = define(function=function_or_node, widgets=widgets)
            self.templatedNewNodes.append((defined_node, defined_actor, params))

        return defined_actor

    async def approve_nodes_and_templates(self):
        await super().approve_nodes_and_templates()
        self.provide_signal.emit(True)
        return 

    async def aprovide(self):
        try:
            await super().aprovide()
        except asyncio.CancelledError as e:
            self.provide_signal.emit(False)
            raise e


    
   

    