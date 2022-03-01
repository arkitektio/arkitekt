from pipes import Template
from typing import Dict, Union
from arkitekt.agents.transport.base import AgentTransport
from arkitekt.arkitekt import Arkitekt, set_current_arkitekt
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
from arkitekt.actors.errors import UnknownMessageError
from arkitekt.actors.vars import current_provision_context

logger = logging.getLogger(__name__)


class Agent:
    transport: AgentTransport
    arkitekt: Arkitekt


class Actor:
    template: TemplateFragment
    transport: AgentTransport
    arkitekt: Arkitekt

    def __init__(
        self,
        provision: Provision,
        agent: Agent,
        *args,
        strict=False,
        expand_inputs=True,
        shrink_outputs=True,
        structure_registry: StructureRegistry = None,
        debug=False,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.strict = strict
        self.expand_inputs = expand_inputs
        self.shrink_outputs = shrink_outputs
        self.structure_registry = structure_registry
        self.runningAssignments: Dict[
            str, asyncio.Task
        ] = {}  # Running assignments indexed by assignment reference
        self.debug = debug
        self.provision = provision
        self.agent = agent
        self.transport = agent.transport
        self.arkitekt = agent.arkitekt

    async def on_provide(self, provision: Provision, template: TemplateFragment):
        return None

    async def on_unprovide(self):
        return None

    async def on_assign(self, assignation: Assignation):
        raise (
            "Needs to be owerwritten in Actor Subclass. Never use this class directly"
        )

    async def apass(self, message: Union[Assignation, Unassignation]):
        await self.in_queue.put(message)

    async def arun(self):
        self.in_queue = asyncio.Queue()
        self.template = await aget_template(
            id=self.provision.template, arkitekt=self.arkitekt
        )
        self.provision_task = asyncio.create_task(self.alisten())

    async def astop(self):
        self.provision_task.cancel()

        try:
            await self.provision_task
        except asyncio.CancelledError:
            print("Provision was cancelled")

    async def alisten(self):
        set_current_arkitekt(self.arkitekt)
        try:
            self.template = await aget_template(id=self.provision.template)

            await self.transport.change_provision(
                self.provision.provision, status=ProvisionStatus.PROVIDING
            )

            prov_context = await self.on_provide(self.provision, self.template)
            current_provision_context.set(prov_context)

            await self.transport.change_provision(
                self.provision.provision,
                status=ProvisionStatus.ACTIVE,
                mode=ProvisionMode.DEBUG if self.debug else ProvisionMode.PRODUCTION,
            )

            while True:
                print("Waiting for assignmements")
                message = await self.in_queue.get()

                if isinstance(message, Assignation):
                    task = asyncio.create_task(self.on_assign(message))
                    self.runningAssignments[message.assignation] = task

                elif isinstance(message, Unassignation):
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
                else:
                    raise UnknownMessageError(f"{message}")

        except Exception as e:
            print(e)
            await self.transport.change_provision(
                self.provision.provision,
                status=ProvisionStatus.CRITICAL,
                message=repr(e),
            )

            current_provision_context.set(None)

        except asyncio.CancelledError as e:
            print("We are getting cancelled here?")
            await self.transport.change_provision(
                self.provision.provision,
                status=ProvisionStatus.CANCELING,
                message=repr(e),
            )

            await self.on_unprovide()

            logger.info("Doing Whatever needs to be done to cancel!")
            await self.transport.change_provision(
                self.provision.provision,
                status=ProvisionStatus.CANCELLED,
                message=str(e),
            )

            cancel_assignations = [i.cancel() for i in self.runningAssignments.values()]

            for i in self.runningAssignments.values():
                try:
                    await i
                except asyncio.CancelledError:
                    pass

            current_provision_context.set(None)
            raise e

    async def __aenter__(self):
        await self.arun()
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.astop()
