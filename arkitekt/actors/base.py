from typing import Dict, Union
from arkitekt.agents.transport.base import AgentTransport
from arkitekt.structures.registry import StructureRegistry
from arkitekt.rath import ArkitektRath
import asyncio
import logging
from arkitekt.api.schema import (
    AssignationStatus,
    ProvisionMode,
    ProvisionStatus,
    aget_template,
    TemplateFragment,
)
from arkitekt.messages import Assignation, Provision, Unassignation
from arkitekt.actors.errors import UnknownMessageError
from arkitekt.actors.vars import current_provision_context

logger = logging.getLogger(__name__)


class Agent:
    transport: AgentTransport
    rath: ArkitektRath


class Actor:
    template: TemplateFragment
    transport: AgentTransport
    rath: ArkitektRath

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
        self.rath = agent.rath

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
        self.template = await aget_template(id=self.provision.template, rath=self.rath)
        self.provision_task = asyncio.create_task(self.alisten())

    async def astop(self):
        self.provision_task.cancel()

        try:
            await self.provision_task
        except asyncio.CancelledError:
            print("Provision was cancelled")

    async def alisten(self):
        try:
            self.template = await aget_template(
                id=self.provision.template, rath=self.rath
            )

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
            logger.info(f"Actor for {self.provision}: Is now active")

            while True:
                message = await self.in_queue.get()
                logger.info(f"Actor for {self.provision}: Received {message}")

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
                        await self.transport.change_assignation(
                            status=AssignationStatus.CRITICAL,
                            message="Task was never assigned",
                        )
                else:
                    raise UnknownMessageError(f"{message}")

        except Exception as e:
            logger.exception("Actor failed", exc_info=True)
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
