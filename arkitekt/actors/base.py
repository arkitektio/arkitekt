

from arkitekt.messages.postman.provide.provide_log import ProvideLogMessage
from arkitekt.messages.postman.log import LogLevel
from arkitekt.monitor.monitor import get_current_monitor
from herre.console.context import get_current_console
from arkitekt.packers.utils import shrink_outputs
from arkitekt.schema.node import Node
from re import template
from arkitekt.messages.postman.assign.assign_cancelled import AssignCancelledMessage
from arkitekt.messages.postman.unassign.bounced_forwarded_unassign import BouncedForwardedUnassignMessage
from herre.auth import get_current_herre
from arkitekt.messages.postman.assign.assign_critical import AssignCriticalMessage
from typing import Dict
from arkitekt.messages.postman.assign.assign_return import AssignReturnMessage
from arkitekt.messages.postman.assign.bounced_forwarded_assign import BouncedForwardedAssignMessage
from arkitekt.messages.postman.assign.bounced_assign import BouncedAssignMessage
from arkitekt.messages.base import MessageModel
from arkitekt.messages.postman.provide.provide_transition import ProvideState
from arkitekt.transport.base import Transport
from arkitekt.packers.transpilers.base import Transpiler
from herre.loop import loopify
from arkitekt.messages.postman.provide.bounced_provide import BouncedProvideMessage
import asyncio
from asyncio.tasks import Task
from arkitekt.messages.postman.provide import ProvideTransitionMessage
import logging
from arkitekt.schema.template import Template



logger = logging.getLogger(__name__)


class Actor:
    transpilers = None
    expand_inputs = True
    shrink_outputs = True

    def __init__(self, provision: BouncedProvideMessage, transport: Transport, loop = None, monitor=None) -> None:
        self.provision = provision
        self.transport = transport
        self.loop = loop or get_current_herre().loop
        self.console = get_current_console()
        self.monitor = monitor or get_current_monitor()
        self.panel = self.monitor.create_actor_panel(self) if self.monitor else None
        self._template = None

        self.runningAssignments: Dict[str, asyncio.Task] = {} # Running assignments indexed by assignment reference


        self.in_queue = asyncio.Queue()
        super().__init__()

    @property
    def template(self) -> Template:
        assert self._template is not None, "We can only access the template after this Actor has been provisioned"
        return self._template


    async def log(self, message, level = LogLevel.INFO):
        if self.panel: self.panel.log(message, level=level)
        logger.info("{level}: {message}")


    async def provide_log(self, message: str, level = LogLevel.INFO):
        await self.transport.forward(ProvideLogMessage(
                data= {
                    "level": level,
                    "message": message
                },
                meta=self.provision.meta.dict(exclude={"type"})
            ))

        if self.panel: self.panel.log(message, level=level)
        logger.info(f"Provide Log: {level}: {message}")


    def run(self, *args, **kwargs):
        return loopify(self.arun(*args, **kwargs))

    async def acall(self, message: MessageModel):
        await self.in_queue.put(message)


    async def on_provide(self, message: BouncedProvideMessage):
        print("Getting Called Here")
        return None


    async def on_unprovide(self, message: BouncedProvideMessage):
        return None


    async def on_assign(self, message: BouncedForwardedAssignMessage):
        raise NotImplementedError("Needs to be owerwritten in Actor Subclass")


    async def arun(self):
        try:
            self._template = await Template.asyncs.get(id=self.provision.data.template)
            
            if self.panel: self.panel.start()

            await self.transport.forward(ProvideTransitionMessage(
                data= {
                    "state": ProvideState.PROVIDING,
                    "message": "We just got started Bay"
                },
                meta={
                    "reference": self.provision.meta.reference,
                    "extensions": self.provision.meta.extensions
                }
            ))



            await self.on_provide(self.provision)

            await self.transport.forward(ProvideTransitionMessage(
                data= {
                    "state": ProvideState.ACTIVE,
                    "message": "We just got started Bay"
                },
                meta={
                    "reference": self.provision.meta.reference,
                    "extensions": self.provision.meta.extensions
                }
            ))

            while True:
                await self.log("Waiting for assignmements")
                message = await self.in_queue.get()
                logger.info(f"Received Message {message}")
                
                if isinstance(message, BouncedForwardedAssignMessage):
                    await self.log("Assigningment received")
                    task = self.loop.create_task(self.on_assign(message))
                    self.runningAssignments[message.meta.reference] = task

                if isinstance(message, BouncedForwardedUnassignMessage):
                    if message.data.assignation in self.runningAssignments:
                        task = self.runningAssignments[message.data.assignation]
                        if not task.done():
                            logger.info("Task is being cancelled")
                            task.cancel()
                        else:
                            logger.error("Task was already done")
                    else:
                        logger.error("Task was never assigned to this actor")
                        if self.string: raise Exception("Received cancellation for Task that was never assinged to this actor!")



        except Exception as e:
            await self.log(f"Provision Exception {str(e)}")
            await self.transport.forward(ProvideTransitionMessage(
                data= {
                    "state": ProvideState.ERROR,
                    "message": f"{e}"
                },
                meta={
                    "reference": self.provision.meta.reference,
                    "extensions": self.provision.meta.extensions
                }
            ))


        except asyncio.CancelledError as e:
            await self.transport.forward(ProvideTransitionMessage(
                data= {
                    "state": ProvideState.CANCELING,
                    "message": f"{e}"
                },
                meta={
                    "reference": self.provision.meta.reference,
                    "extensions": self.provision.meta.extensions
                }
            ))

            await self.on_unprovide(self.provision)


            logger.info("Doing Whatever needs to be done to cancel!")
            await self.transport.forward(ProvideTransitionMessage(
                data= {
                    "state": ProvideState.CANCELLED,
                    "message": f"{e}"
                },
                meta={
                    "reference": self.provision.meta.reference,
                    "extensions": self.provision.meta.extensions
                }
            ))
            raise e

        if self.panel: self.panel.end()




