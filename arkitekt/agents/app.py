


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

logger = logging.getLogger(__name__)


class AppAgent(Agent):
    ACTOR_PENDING_MESSAGE = "Actor is Pending"

    def __init__(self, *args, strict=False, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.potentialNodes: List[Tuple[Node, Callable]] = []
        self.potentialTemplates: List[Tuple[Node, Callable]] = []
        self.approvedTemplates: List[Tuple[Template, Callable]] = []
        self.approvedActors: Dict[str, Type[Actor]] = {}
        self.strict = strict

        # Running Actors indexed by their ID
        self.runningActors: Dict[str, Actor] = {}
        self.runningTasks: Dict[str, asyncio.Task] = {}

    def on_task_done(self, future):
        print(future)

    async def on_bounced_provide(self, message: BouncedProvideMessage):
        
        if message.data.template in self.approvedActors:
            if message.meta.reference in self.runningActors:
                if self.strict: raise AgentException("Already Running Provision Received Again. Right now causing Error. Might be omitted")
                again_provided = ProvideTransitionMessage(data={
                    "message": "Provision was running on this Instance. Probably a freaking race condition",
                    "state": ProvideState.ACTIVE
                    }, meta={"extensions": message.meta.extensions, "reference": message.meta.reference})
                await self.transport.forward(again_provided)
            else:
                actor = self.approvedActors[message.data.template](message, self.transport, monitor=self.monitor)
                self.runningActors[message.meta.reference] = actor
                task = self.loop.create_task(actor.arun())
                task.add_done_callback(self.on_task_done)
                self.runningTasks[message.meta.reference] = task

        else:
            raise AgentException("No approved actors for this template")


    async def on_bounced_unprovide(self, message: BouncedUnprovideMessage):
        if message.data.provision not in self.runningActors: raise AgentException("Already Running Provision Received Again. Right now causing Error. Might be omitted")
        actor = self.runningActors[message.data.provision]
        
        logger.info(f"Cancelling {actor}")
        self.runningTasks[message.data.provision].cancel()

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
                

    
    async def handle_bounced_provide(self, message: BouncedProvideMessage):
        try:
            await self.on_bounced_provide(message)

            progress = ProvideLogMessage(data={
            "level": LogLevel.INFO,
            "message": f"Actor Pending"
            }, meta={"extensions": message.meta.extensions, "reference": message.meta.reference})

            await self.transport.forward(progress)


        except Exception as e:
            logger.error(e)
            critical_error = ProvideTransitionMessage(data={
            "message": str(e),
            "state": ProvideState.CRITICAL
            }, meta={"extensions": message.meta.extensions, "reference": message.meta.reference})
            await self.transport.forward(critical_error)


    async def handle_bounced_unprovide(self, message: BouncedUnprovideMessage):
        try:
            await self.on_bounced_unprovide(message)

            progress = ProvideLogMessage(data={
            "level": LogLevel.INFO,
            "message": f"Actor Delation Happening"
            }, meta={"extensions": message.meta.extensions, "reference": message.meta.reference})

            await self.transport.forward(progress)


        except Exception as e:
            logger.error(e)
            critical_error = ProvideTransitionMessage(data={
            "message": str(e),
            "state": ProvideState.CRITICAL
            }, meta={"extensions": message.meta.extensions, "reference": message.meta.reference})
            await self.transport.forward(critical_error)
     

    async def handle_bounced_assign(self, message: BouncedForwardedAssignMessage):
        try:
            await self.on_bounced_assign(message)

            progress = AssignLogMessage(data={
            "level": LogLevel.INFO,
            "message": f"Assign Forwarded from Worker"
            }, meta={"extensions": message.meta.extensions, "reference": message.meta.reference})

            await self.transport.forward(progress)


        except Exception as e:
            logger.error(e)
            critical_error = AssignCriticalMessage(data={
            "message": str(e),
            "type": e.__class__.__name__
            }, meta={"extensions": message.meta.extensions, "reference": message.meta.reference})
            await self.transport.forward(critical_error)
            raise e

    async def handle_bounced_unassign(self, message: BouncedForwardedUnassignMessage):
        try:
            await self.on_bounced_unassign(message)

            progress = AssignLogMessage(data={
            "level": LogLevel.INFO,
            "message": f"Unassignation was send to the assignation"
            }, meta={"extensions": message.meta.extensions, "reference": message.data.assignation})

            await self.transport.forward(progress)


        except Exception as e:
            logger.error(e)
            critical_error = AssignCriticalMessage(data={
            "message": str(e),
            "type": e.__class__.__name__
            }, meta={"extensions": message.meta.extensions, "reference": message.data.assignation})
            await self.transport.forward(critical_error)
            raise e


    def register(self, *args, widgets={}, transpilers: Dict[str, Transpiler] = None, on_provide = None, on_unprovide = None, **params):

        def real_decorator(function):
            # Simple bypass for now
            def wrapped_function(*args, **kwargs):
                return function(*args, **kwargs)

            if len(args) == 0:
                defined_node = define(function=function, widgets=widgets)
                defined_actor = actify(function, on_provide=on_provide, on_unprovide=on_unprovide, **params)


                self.potentialNodes.append((defined_node, defined_actor, params))

            if len(args) == 1:
                print("Hallo")
                # We are registering this as a template
                

            return wrapped_function

    
        return real_decorator

    
   


    async def providing_loop(self):


        await self.transport.connect()

        while True:
            await asyncio.sleep(3)

        if self.monitor: self.monitor.__exit__()
        if self.panel: self.panel.end()



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
        # Connection Started
        if not self.connected: 
            await self.connect()

        
        if self.monitor: self.monitor.__enter__()
        if self.panel: self.panel.start()

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
        
        
        await self.providing_loop()