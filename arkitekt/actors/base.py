from typing import Dict, Union
from arkitekt.agents.transport.base import AgentTransport
from arkitekt.structures.registry import StructureRegistry
import asyncio
import logging
from arkitekt.api.schema import (
    ProvisionMode,
    ProvisionStatus,
    aget_template,
    TemplateFragment,
)
from arkitekt.messages import Assignation, Provision, Unassignation, Unprovision

logger = logging.getLogger(__name__)


class Actor:
    template: TemplateFragment
    transport: AgentTransport

    def __init__(
        self,
        *args,
        strict=False,
        expand_inputs=True,
        shrink_outputs=True,
        transpilers={},
        structure_registry: StructureRegistry = None,
        debug=False,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.strict = strict
        self.layer = None
        self.expand_inputs = expand_inputs
        self.shrink_outputs = shrink_outputs
        self.structure_registry = structure_registry
        self.runningAssignments: Dict[
            str, asyncio.Task
        ] = {}  # Running assignments indexed by assignment reference
        self.debug = debug

    async def on_provide(self, message: Provision):
        return None

    async def on_unprovide(self):
        return None

    async def apass(self, message: Union[Assignation, Unassignation]):
        await self.in_queue.put(message)

    async def arun(self, provision: Provision, agent):
        self.loop = asyncio.get_running_loop()
        self.provision = provision
        self.agent = agent
        self.transport = agent.transport
        self.in_queue = asyncio.Queue()

        try:
            self.template = await aget_template(id=self.provision.template)

            await self.transport.change_provision(
                self.provision.provision, status=ProvisionStatus.PROVIDING
            )

            await self.on_provide(self.provision)

            await self.transport.change_provision(
                self.provision.provision,
                status=ProvisionStatus.ACTIVE,
                mode=ProvisionMode.DEBUG if self.debug else ProvisionMode.PRODUCTION,
            )

            while True:
                print("Waiting for assignmements")
                message = await self.in_queue.get()
                logger.info(f"Received Message {message}")

                if isinstance(message, Assignation):
                    task = asyncio.create_task(self.on_assign(message))
                    self.runningAssignments[message.assignation] = task

                if isinstance(message, Unassignation):
                    if message.assignation in self.runningAssignments:
                        task = self.runningAssignments[message.assignation]
                        if not task.done():
                            print("Cancelling task")
                            task.cancel()
                        else:
                            logger.error("Task was already done")
                    else:
                        await self.layer.change_assignation(
                            message="Task was never assigned"
                        )

                print(message)
                raise NotImplementedError("Needs to be owerwritten in Actor Subclass")

        except Exception as e:
            print(e)
            await self.transport.change_provision(
                self.provision.provision,
                status=ProvisionStatus.CRITICAL,
                message=str(e),
            )

        except asyncio.CancelledError as e:

            await self.transport.change_provision(
                self.provision.provision,
                status=ProvisionStatus.CANCELING,
                message=str(e),
            )

            await self.on_unprovide()

            logger.info("Doing Whatever needs to be done to cancel!")
            await self.transport.change_provision(
                self.provision.provision,
                status=ProvisionStatus.CANCELLED,
                message=str(e),
            )
            raise e
