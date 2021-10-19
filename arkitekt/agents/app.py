


from arkitekt.agents.standard import StandardAgent
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


class AppAgent(StandardAgent):
    ACTOR_PENDING_MESSAGE = "Actor is Pending"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Running Actors indexed by their ID
        self.runningActors: Dict[str, Actor] = {}
        self.runningTasks: Dict[str, asyncio.Task] = {}

        self.templatedUnqueriedNodes:  List[Tuple[dict, Callable]] = [] # dict are queryparams for the node
        self.templatedNodes: List[Tuple[Node, Callable]] = [] # node is already saved and has id
        self.templatedNewNodes: List[Tuple[Node, Callable]] = [] # Node is not saved and has undefined id


        self.approvedTemplates: List[Tuple[Template, Callable]] = [] # Template is approved 


        # IMportant Maps
        self.templateActorsMap = {}
        self.templateTemplatesMap = {}



    async def on_transport_about_to_connect(self):
        await self.approve_nodes_and_templates()
        return 

    async def on_transport_connected(self):
        print(f"Hosting {self.templateActorsMap.keys()}")


    def on_task_done(self, future):
        print(future)


    async def on_bounced_provide(self, message: BouncedProvideMessage):
        
        if message.data.template in self.templateActorsMap:
            if message.meta.reference not in self.runningActors:
                # Didn not exist before
                actor = self.templateActorsMap[message.data.template] # creating out little Actor
                self.runningActors[message.meta.reference] = actor
                task = self.loop.create_task(actor.arun(message, self))
                task.add_done_callback(self.on_task_done)
                self.runningTasks[message.meta.reference] = task
                
            else:
                if self.strict: raise AgentException("Already Running Provision Received Again. Right now causing Error. Might be omitted")
                again_provided = ProvideTransitionMessage(data={
                    "message": "Provision was running on this Instance. Probably a freaking race condition",
                    "state": ProvideState.ACTIVE
                    }, meta={"extensions": message.meta.extensions, "reference": message.meta.reference})
                await self.transport.forward(again_provided)

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
                




    async def approve_nodes_and_templates(self):

        if self.templatedUnqueriedNodes:
            for query_params, defined_actor, params in self.templatedUnqueriedNodes:
                try:
                    arkitekt_node = await Node.asyncs.get(**query_params)
                    self.templatedNodes.append((arkitekt_node, defined_actor, params))
                except WardException as e:
                    logger.exception(e)
                    if self.strict: raise AgentException(f"Couldn't find Node for query {query_params}") from e   

        if self.templatedNewNodes:
            for defined_node, defined_actor, params in self.templatedNewNodes:
                # Defined Node are nodes that are not yet reflected on arkitekt (i.e they dont have an instance
                # id so we are trying to send them to arkitekt)
                try:
                    arkitekt_node = await Node.asyncs.create(**defined_node.dict(as_input=True))
                    self.templatedNodes.append((arkitekt_node, defined_actor, params))   
                except WardException as e:
                    logger.exception(e)
                    if self.strict: raise AgentException(f"Couldn't create Node for defintion {defined_node}") from e

        if self.templatedNodes:
            # This is an arkitekt Node and we can generate potential Templates
            for arkitekt_node, defined_actor, params in self.templatedNodes:
                try:
                    params = await parse_params(params) # Parse the parameters for template creation
                    arkitekt_template = await Template.asyncs.create(node=arkitekt_node, params=params)
                    self.approvedTemplates.append((arkitekt_template, defined_actor, params))  
                except WardException as e:
                    logger.exception(e)
                    if self.strict: raise AgentException(f"Couldn't approve template for node {arkitekt_node}") from e

        if self.approvedTemplates:

            for arkitekt_template, defined_actor, params in self.approvedTemplates:

                # Generating Maps for Easy access
                self.templateActorsMap[arkitekt_template.id] = defined_actor
                self.templateTemplatesMap[arkitekt_template.id] = arkitekt_template

                if self.panel: self.panel.add_to_actor_map(arkitekt_template, defined_actor) 



    def register(self, *args, widgets={}, transpilers: Dict[str, Transpiler] = None, on_provide = None, on_unprovide = None, **params):

        def real_decorator(function):
            # Simple bypass for now
            def wrapped_function(*args, **kwargs):
                return function(*args, **kwargs)

            
            defined_actor = actify(function, on_provide=on_provide, on_unprovide=on_unprovide, **params)

            if len(args) == 0:
                defined_node = define(function=function, widgets=widgets)
                self.templatedNewNodes.append((defined_node, defined_actor, params))

            if len(args) == 1:
                if isinstance(args[0], str):
                    self.templatedUnqueriedNodes.append(({"q": args[0]}, defined_actor, params))

                if isinstance(args[0], Node):
                    self.templatedNodes.append((args[0], defined_actor, params))

                # We are registering this as a template

            return wrapped_function

    
        return real_decorator
