import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable, Optional

from arkitekt.actors.base import Actor
from arkitekt.actors.helper import AsyncAssignationHelper, ThreadedAssignationHelper
from arkitekt.actors.vars import current_assignation_helper
from arkitekt.api.schema import AssignationStatus
from arkitekt.messages import Assignation, Provision
from arkitekt.structures.serialization.actor import expand_inputs, shrink_outputs
from koil.helpers import iterate_spawned, run_spawned
from pydantic import Field

logger = logging.getLogger(__name__)


class FunctionalActor(Actor):
    assign: Callable[..., Any]
    provide: Optional[Callable[[Provision], Awaitable[Any]]]
    unprovide: Optional[Callable[[], Awaitable[Any]]]


class FunctionalFuncActor(FunctionalActor):
    async def progress(self, value, percentage):
        await self._progress(value, percentage)

    async def on_assign(self, assignation: Assignation):
        try:
            args, kwargs = (
                await expand_inputs(
                    self.template.node,
                    assignation.args,
                    assignation.kwargs,
                    structure_registry=self.structure_registry,
                )
                if self.expand_inputs
                else (assignation.args, assignation.kwargs)
            )

            await self.transport.change_assignation(
                assignation.assignation,
                status=AssignationStatus.ASSIGNED,
            )

            current_assignation_helper.set(
                AsyncAssignationHelper(
                    actor=self, assignation=assignation, provision=self.provision
                )
            )

            returns = await self.assign(*args, **kwargs)

            current_assignation_helper.set(None)

            returns = (
                await shrink_outputs(
                    self.template.node,
                    returns,
                    structure_registry=self.structure_registry,
                )
                if self.shrink_outputs
                else returns
            )

            await self.transport.change_assignation(
                assignation.assignation,
                status=AssignationStatus.RETURNED,
                returns=returns,
            )

        except asyncio.CancelledError as e:

            await self.transport.change_assignation(
                assignation.assignation, status=AssignationStatus.CANCELLED
            )

        except Exception as e:
            logger.exception(e)
            await self.transport.change_assignation(
                assignation.assignation,
                status=AssignationStatus.CRITICAL,
                message=repr(e),
            )


class FunctionalGenActor(FunctionalActor):
    async def progress(self, value, percentage):
        await self._progress(value, percentage)

    async def on_assign(self, message: Assignation):
        try:
            args, kwargs = (
                await expand_inputs(
                    self.template.node,
                    message.args,
                    message.kwargs,
                    structure_registry=self.structure_registry,
                )
                if self.expand_inputs
                else (message.args, message.kwargs)
            )

            current_assignation_helper.set(
                AsyncAssignationHelper(
                    actor=self, assignation=message, provision=self.provision
                )
            )

            await self.transport.change_assignation(
                message.assignation,
                status=AssignationStatus.ASSIGNED,
            )

            async for returns in self.assign(*args, **kwargs):

                returns = (
                    await shrink_outputs(
                        self.template.node,
                        returns,
                        structure_registry=self.structure_registry,
                    )
                    if self.shrink_outputs
                    else returns
                )

                await self.transport.change_assignation(
                    message.assignation, status=AssignationStatus.YIELD, returns=returns
                )

            current_assignation_helper.set(None)

            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.DONE
            )

        except asyncio.CancelledError as e:

            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.CANCELLED, message=str(e)
            )

        except Exception as e:
            logger.error("Error in actor", exc_info=True)
            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.CRITICAL, message=str(e)
            )

            raise e


class FunctionalThreadedFuncActor(FunctionalActor):
    threadpool: ThreadPoolExecutor = Field(
        default_factory=lambda: ThreadPoolExecutor(4)
    )

    async def on_assign(self, message: Assignation):

        try:
            logger.info("Assigning Number two")
            args, kwargs = (
                await expand_inputs(
                    self.template.node,
                    message.args,
                    message.kwargs,
                    structure_registry=self.structure_registry,
                )
                if self.expand_inputs
                else (message.args, message.kwargs)
            )

            await self.transport.change_assignation(
                message.assignation,
                status=AssignationStatus.ASSIGNED,
            )

            current_assignation_helper.set(
                ThreadedAssignationHelper(
                    actor=self, assignation=message, provision=self.provision
                )
            )
            returns = await run_spawned(self.assign, *args, **kwargs, pass_context=True)

            current_assignation_helper.set(None)
            shrinked_returns = (
                await shrink_outputs(
                    self.template.node,
                    returns,
                    structure_registry=self.structure_registry,
                )
                if self.expand_inputs
                else (message.args, message.kwargs)
            )

            await self.transport.change_assignation(
                message.assignation,
                status=AssignationStatus.RETURNED,
                returns=shrinked_returns,
            )

        except asyncio.CancelledError as e:
            logger.info("Actor Cancelled")

            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.CANCELLED, message=str(e)
            )

        except Exception as e:
            logger.error("Error in actor", exc_info=True)
            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.CRITICAL, message=str(e)
            )


class FunctionalThreadedGenActor(FunctionalActor):
    threadpool: ThreadPoolExecutor = Field(
        default_factory=lambda: ThreadPoolExecutor(4)
    )

    async def on_assign(self, message: Assignation):
        try:
            args, kwargs = (
                await expand_inputs(
                    self.template.node,
                    message.args,
                    message.kwargs,
                    structure_registry=self.structure_registry,
                )
                if self.expand_inputs
                else (message.args, message.kwargs)
            )

            current_assignation_helper.set(
                ThreadedAssignationHelper(
                    actor=self, assignation=message, provision=self.provision
                )
            )

            await self.transport.change_assignation(
                message.assignation,
                status=AssignationStatus.ASSIGNED,
            )

            async for returns in iterate_spawned(
                self.assign, *args, **kwargs, pass_context=True
            ):

                returns = (
                    await shrink_outputs(
                        self.template.node,
                        returns,
                        structure_registry=self.structure_registry,
                    )
                    if self.shrink_outputs
                    else returns
                )

                await self.transport.change_assignation(
                    message.assignation, status=AssignationStatus.YIELD, returns=returns
                )

            current_assignation_helper.set(None)

            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.DONE
            )

        except asyncio.CancelledError as e:

            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.CANCELLED, message=str(e)
            )

        except Exception as e:
            logger.error("Error in actor", exc_info=True)
            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.CRITICAL, message=str(e)
            )

            raise e
