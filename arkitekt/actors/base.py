from arkitekt.messages.postman.provide.provide_log import ProvideLogMessage
from arkitekt.messages.postman.log import LogLevel
from arkitekt.monitor.monitor import AgentPanel, get_current_monitor
from herre.console.context import get_current_console
from arkitekt.packers.utils import shrink_outputs
from re import template
from arkitekt.messages.postman.assign.assign_cancelled import AssignCancelledMessage
from arkitekt.messages.postman.unassign.bounced_forwarded_unassign import (
    BouncedForwardedUnassignMessage,
)
from arkitekt.messages.postman.assign.assign_critical import AssignCriticalMessage
from typing import Dict
from arkitekt.messages.postman.assign.assign_return import AssignReturnMessage
from arkitekt.messages.postman.assign.bounced_forwarded_assign import (
    BouncedForwardedAssignMessage,
)
from arkitekt.messages.postman.assign.bounced_assign import BouncedAssignMessage
from arkitekt.messages.base import MessageModel
from arkitekt.messages.postman.provide.provide_transition import (
    ProvideMode,
    ProvideState,
)
from arkitekt.transport.base import Transport
from arkitekt.packers.transpilers.base import Transpiler
from arkitekt.messages.postman.provide.bounced_provide import BouncedProvideMessage
import asyncio
from asyncio.tasks import Task, create_task
from arkitekt.messages.postman.provide import ProvideTransitionMessage
import logging
from arkitekt.schema.template import Template
from koil.koil import Koil, get_current_koil
from koil.loop import koil


logger = logging.getLogger(__name__)


class Actor:
    template: Template

    def __init__(
        self,
        *args,
        koil: Koil = None,
        strict=False,
        expand_inputs=True,
        shrink_outputs=True,
        transpilers={},
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.strict = strict
        self.expand_inputs = expand_inputs
        self.shrink_outputs = shrink_outputs
        self.runningAssignments: Dict[
            str, asyncio.Task
        ] = {}  # Running assignments indexed by assignment reference

    async def log(self, message, level=LogLevel.INFO):
        logger.info("{level}: {message}")

    async def provide_log(self, message: str, level=LogLevel.INFO):
        await self.agent.transport.forward(
            ProvideLogMessage(
                data={"level": level, "message": message},
                meta=self.provision.meta.dict(exclude={"type"}),
            )
        )
        logger.info(f"Provide Log: {level}: {message}")

    def run(self, *args, **kwargs):
        return koil(self.arun(*args, **kwargs))

    async def acall(self, message: MessageModel):
        await self.in_queue.put(message)

    async def on_provide(self, message: BouncedProvideMessage):
        return None

    async def on_unprovide(self, message: BouncedProvideMessage):
        return None

    async def on_assign(self, message: BouncedForwardedAssignMessage):
        raise NotImplementedError("Needs to be owerwritten in Actor Subclass")

    async def arun(self, provision: BouncedProvideMessage, agent):
        self.loop = asyncio.get_running_loop()
        self.provision = provision
        self.agent = agent
        self.transport = agent.transport
        self.in_queue = asyncio.Queue()

        try:
            self.template = await Template.asyncs.get(id=self.provision.data.template)

            await self.transport.forward(
                ProvideTransitionMessage(
                    data={
                        "state": ProvideState.PROVIDING,
                        "message": "We just got started Bay",
                    },
                    meta={
                        "reference": self.provision.meta.reference,
                        "extensions": self.provision.meta.extensions,
                    },
                )
            )

            await self.on_provide(self.provision)

            await self.transport.forward(
                ProvideTransitionMessage(
                    data={
                        "state": ProvideState.ACTIVE,
                        "message": "We just got started Bay",
                        "mode": ProvideMode.DEBUG
                        if agent.config.debug
                        else ProvideMode.PRODUCTION,
                    },
                    meta={
                        "reference": self.provision.meta.reference,
                        "extensions": self.provision.meta.extensions,
                    },
                )
            )

            while True:
                await self.log("Waiting for assignmements")
                message = await self.in_queue.get()
                logger.info(f"Received Message {message}")

                if isinstance(message, BouncedForwardedAssignMessage):
                    await self.log("Assigningment received")
                    task = create_task(self.on_assign(message))
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
                        if self.strict:
                            raise Exception(
                                "Received cancellation for Task that was never assinged to this actor!"
                            )
                        await self.transport.forward(
                            AssignCancelledMessage(
                                data={
                                    "canceller": str(
                                        "Cancelled because actor receiving this cancellation never had this task but was also not strict"
                                    )
                                },
                                meta={
                                    "reference": message.data.assignation,
                                    "extensions": message.meta.extensions,
                                },
                            )
                        )

        except Exception as e:
            logger.exception(e)
            await self.log(f"Provision Exception {str(e)}")
            await self.transport.forward(
                ProvideTransitionMessage(
                    data={"state": ProvideState.CRITICAL, "message": f"{e}"},
                    meta={
                        "reference": self.provision.meta.reference,
                        "extensions": self.provision.meta.extensions,
                    },
                )
            )

        except asyncio.CancelledError as e:

            await self.transport.forward(
                ProvideTransitionMessage(
                    data={"state": ProvideState.CANCELING, "message": f"{e}"},
                    meta={
                        "reference": self.provision.meta.reference,
                        "extensions": self.provision.meta.extensions,
                    },
                )
            )

            await self.on_unprovide(self.provision)

            logger.info("Doing Whatever needs to be done to cancel!")
            await self.transport.forward(
                ProvideTransitionMessage(
                    data={"state": ProvideState.CANCELLED, "message": f"{e}"},
                    meta={
                        "reference": self.provision.meta.reference,
                        "extensions": self.provision.meta.extensions,
                    },
                )
            )
            raise e
