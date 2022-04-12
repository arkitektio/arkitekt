from typing import Dict, Optional, Union

from pydantic import BaseModel, Field
from arkitekt.agents.transport.base import AgentTransport
from arkitekt.structures.registry import (
    StructureRegistry,
    get_current_structure_registry,
)
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
from koil.types import Contextual

logger = logging.getLogger(__name__)


class Actor(BaseModel):
    provision: Provision
    transport: AgentTransport

    strict: bool = False
    expand_inputs: bool = True
    shrink_outputs: bool = True
    structure_registry: StructureRegistry = Field(
        default_factory=get_current_structure_registry
    )
    rath: Optional[ArkitektRath] = Field(default=None)

    template: Contextual[TemplateFragment] = None
    debug: bool = False

    runningAssignments: Dict[str, Assignation] = Field(default_factory=dict)

    _in_queue: Contextual[asyncio.Queue] = None
    _runningTasks: Dict[str, asyncio.Task] = {}
    _provision_task: asyncio.Task = None

    async def on_provide(self, provision: Provision, template: TemplateFragment):
        return None

    async def on_unprovide(self):
        return None

    async def on_assign(self, assignation: Assignation):
        raise (
            "Needs to be owerwritten in Actor Subclass. Never use this class directly"
        )

    async def apass(self, message: Union[Assignation, Unassignation]):
        assert hasattr(self, "_in_queue"), "Actor is currently not listening"
        await self._in_queue.put(message)

    async def arun(self):
        self._in_queue = asyncio.Queue()
        self._provision_task = asyncio.create_task(self.alisten())

    async def astop(self):
        self._provision_task.cancel()

        try:
            await self._provision_task
        except asyncio.CancelledError:
            print("Provision was cancelled")

    async def alisten(self):
        self.template = await aget_template(id=self.provision.template, rath=self.rath)
        try:
            self.template = await aget_template(
                id=self.provision.template, rath=self.rath
            )

            await self.transport.change_provision(
                self.provision.provision, status=ProvisionStatus.PROVIDING
            )

            prov_context = await self.on_provide(self.provision, self.template)

            await self.transport.change_provision(
                self.provision.provision,
                status=ProvisionStatus.ACTIVE,
                mode=ProvisionMode.DEBUG if self.debug else ProvisionMode.PRODUCTION,
            )
            logger.info(f"Actor for {self.provision}: Is now active")

            while True:
                message = await self._in_queue.get()
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
            print(e)
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

            cancel_assignations = [i.cancel() for i in self.runningAssignments.values()]

            for i in self.runningAssignments.values():
                try:
                    await i
                except asyncio.CancelledError:
                    pass

            await self.transport.change_provision(
                self.provision.provision,
                status=ProvisionStatus.CANCELLED,
                message=str(e),
            )
            raise e

    async def __aenter__(self):
        await self.arun()
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.astop()

    class Config:
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True
