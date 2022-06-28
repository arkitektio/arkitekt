import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable, Optional
from koil.helpers import iterate_spawned, run_spawned
from pydantic import BaseModel, Field
from arkitekt.actors.base import Actor
from arkitekt.actors.helper import AsyncAssignationHelper, ThreadedAssignationHelper
from arkitekt.actors.vars import current_assignation_helper
from arkitekt.api.schema import AssignationStatus
from arkitekt.messages import Assignation, Provision
from arkitekt.structures.serialization.actor import expand_inputs, shrink_outputs


logger = logging.getLogger(__name__)


class FunctionalActor(BaseModel):
    assign: Callable[..., Any]
    provide: Optional[Callable[[Provision], Awaitable[Any]]]
    unprovide: Optional[Callable[[], Awaitable[Any]]]

    class Config:
        arbitrary_types_allowed = True


class AsyncFuncActor(Actor):
    async def on_assign(self, assignation: Assignation):
        logging.info("Assigning %s", assignation)
        try:
            args, kwargs = (
                await expand_inputs(
                    self.provision.template.node,
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
                    self.provision.template.node,
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

        except asyncio.CancelledError:

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


class AsyncGenActor(Actor):
    async def on_assign(self, assignation: Assignation):
        try:
            args, kwargs = (
                await expand_inputs(
                    self.provision.template.node,
                    assignation.args,
                    assignation.kwargs,
                    structure_registry=self.structure_registry,
                )
                if self.expand_inputs
                else (assignation.args, assignation.kwargs)
            )

            current_assignation_helper.set(
                AsyncAssignationHelper(
                    actor=self, assignation=assignation, provision=self.provision
                )
            )

            await self.transport.change_assignation(
                assignation.assignation,
                status=AssignationStatus.ASSIGNED,
            )

            async for returns in self.assign(*args, **kwargs):

                returns = (
                    await shrink_outputs(
                        self.provision.template.node,
                        returns,
                        structure_registry=self.structure_registry,
                    )
                    if self.shrink_outputs
                    else returns
                )

                await self.transport.change_assignation(
                    assignation.assignation,
                    status=AssignationStatus.YIELD,
                    returns=returns,
                )

            current_assignation_helper.set(None)

            await self.transport.change_assignation(
                assignation.assignation, status=AssignationStatus.DONE
            )

        except asyncio.CancelledError:

            await self.transport.change_assignation(
                assignation.assignation, status=AssignationStatus.CANCELLED
            )

        except Exception as ex:
            logger.error("Error in actor", exc_info=True)
            await self.transport.change_assignation(
                assignation.assignation,
                status=AssignationStatus.CRITICAL,
                message=str(ex),
            )

            raise ex


class FunctionalFuncActor(FunctionalActor, AsyncFuncActor):
    async def progress(self, value, percentage):
        await self._progress(value, percentage)

    class Config:
        arbitrary_types_allowed = True


class FunctionalGenActor(FunctionalActor, AsyncGenActor):
    async def progress(self, value, percentage):
        await self._progress(value, percentage)

    class Config:
        arbitrary_types_allowed = True


class ThreadedFuncActor(Actor):
    threadpool: ThreadPoolExecutor = Field(
        default_factory=lambda: ThreadPoolExecutor(4)
    )

    async def on_assign(self, assignation: Assignation):

        try:
            logger.info("Assigning Number two")
            args, kwargs = (
                await expand_inputs(
                    self.provision.template.node,
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
                ThreadedAssignationHelper(
                    actor=self, assignation=assignation, provision=self.provision
                )
            )
            print("OINOINOINO")
            returns = await run_spawned(self.assign, *args, **kwargs, pass_context=True)

            current_assignation_helper.set(None)
            shrinked_returns = (
                await shrink_outputs(
                    self.provision.template.node,
                    returns,
                    structure_registry=self.structure_registry,
                )
                if self.expand_inputs
                else (assignation.args, assignation.kwargs)
            )

            await self.transport.change_assignation(
                assignation.assignation,
                status=AssignationStatus.RETURNED,
                returns=shrinked_returns,
            )

        except asyncio.CancelledError as e:
            logger.info("Actor Cancelled")

            await self.transport.change_assignation(
                assignation.assignation,
                status=AssignationStatus.CANCELLED,
                message=str(e),
            )

        except Exception as e:
            logger.error("Error in actor", exc_info=True)
            await self.transport.change_assignation(
                assignation.assignation,
                status=AssignationStatus.CRITICAL,
                message=str(e),
            )


class ThreadedGenActor(Actor):
    threadpool: ThreadPoolExecutor = Field(
        default_factory=lambda: ThreadPoolExecutor(4)
    )

    async def on_assign(self, assignation: Assignation):
        try:
            args, kwargs = (
                await expand_inputs(
                    self.provision.template.node,
                    assignation.args,
                    assignation.kwargs,
                    structure_registry=self.structure_registry,
                )
                if self.expand_inputs
                else (assignation.args, assignation.kwargs)
            )

            current_assignation_helper.set(
                ThreadedAssignationHelper(
                    actor=self, assignation=assignation, provision=self.provision
                )
            )

            await self.transport.change_assignation(
                assignation.assignation,
                status=AssignationStatus.ASSIGNED,
            )

            async for returns in iterate_spawned(
                self.assign, *args, **kwargs, pass_context=True
            ):

                returns = (
                    await shrink_outputs(
                        self.provision.template.node,
                        returns,
                        structure_registry=self.structure_registry,
                    )
                    if self.shrink_outputs
                    else returns
                )

                await self.transport.change_assignation(
                    assignation.assignation,
                    status=AssignationStatus.YIELD,
                    returns=returns,
                )

            current_assignation_helper.set(None)

            await self.transport.change_assignation(
                assignation.assignation, status=AssignationStatus.DONE
            )

        except asyncio.CancelledError as e:

            await self.transport.change_assignation(
                assignation.assignation,
                status=AssignationStatus.CANCELLED,
                message=str(e),
            )

        except Exception as e:
            logger.error("Error in actor", exc_info=True)
            await self.transport.change_assignation(
                assignation.assignation,
                status=AssignationStatus.CRITICAL,
                message=str(e),
            )

            raise e


class FunctionalThreadedFuncActor(FunctionalActor, ThreadedFuncActor):
    async def progress(self, value, percentage):
        await self._progress(value, percentage)

    class Config:
        arbitrary_types_allowed = True


class FunctionalThreadedGenActor(FunctionalActor, ThreadedGenActor):
    async def progress(self, value, percentage):
        await self._progress(value, percentage)

    class Config:
        arbitrary_types_allowed = True
