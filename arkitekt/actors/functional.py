import threading
from typing import Any, Coroutine
from arkitekt.actors.exceptions import ThreadedActorCancelled
from arkitekt.messages import Assignation
from arkitekt.api.schema import AssignationStatus
from arkitekt.actors.base import Actor
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import asyncio
from arkitekt.structures.serialization.actor import expand_inputs, shrink_outputs
from arkitekt.actors.vars import (
    current_assignation,
    current_janus_queue,
    current_cancel_event,
)
import logging
import janus


logger = logging.getLogger(__name__)


class FunctionalActor(Actor):
    pass

    def __init__(
        self, *args, assign=None, on_provide=None, on_unprovide=None, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.assign = assign or self.assign
        self.on_provide = on_provide or self.on_provide
        self.on_unprovide = on_unprovide or self.on_unprovide

    def assign(self, *args, **kwargs):
        raise NotImplementedError("Please overwrite this")


class FunctionalFuncActor(FunctionalActor):
    assign: Coroutine[Any, Any, Any]

    async def progress(self, value, percentage):
        await self._progress(value, percentage)

    async def on_assign(self, assignation: Assignation):
        try:
            logger.info("Assigning Number two")
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

            current_assignation.set(assignation)

            returns = await self.assign(*args, **kwargs)

            current_assignation.set(None)

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
                results=returns,
            )

        except asyncio.CancelledError as e:

            await self.transport.change_assignation(
                assignation.assignation, status=AssignationStatus.CANCELLED
            )

        except Exception as e:
            logger.exception(e)
            await self.transport.change_assignation(
                assignation.assignation, status=AssignationStatus.CRITICAL
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

            current_assignation.set(message)

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
                    message.assignation, status=AssignationStatus.YIELD, results=returns
                )

            current_assignation.set(None)

            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.DONE
            )

        except asyncio.CancelledError as e:

            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.CANCEL
            )

        except Exception as e:
            logger.exception(e)
            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.CRITICAL
            )


class FunctionalThreadedFuncActor(FunctionalActor):
    def __init__(self, *args, nworkers=4, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.threadpool = ThreadPoolExecutor(nworkers)

    async def iterate_queue(self, async_q, message: Assignation):
        try:
            while True:
                val = await async_q.get()
                action = val[0]
                value = val[1]

                if action == "log":
                    message = AssignLogMessage(
                        data={"message": value[0], "level": value[1]},
                        meta={**message.meta.dict(exclude={"type"})},
                    )

                    await self.transport.forward(message)
                    async_q.task_done()
                if action == "return":

                    returns = (
                        await shrink_outputs(
                            self.template.node,
                            value,
                            structure_registry=self.structure_registry,
                        )
                        if self.shrink_outputs
                        else value
                    )

                    await self.layer.change_assignation(
                        message.assignation,
                        status=AssignationStatus.RETURNED,
                        resulsts=returns,
                    )
                    async_q.task_done()
                    break
                if action == "exception":
                    async_q.task_done()
                    raise value

        except asyncio.CancelledError as cancelled_error:
            logger.info(f"Received Cancellation to iterate over async queue")
            while True:
                val = await async_q.get()
                action = val[0]
                value = val[1]
                if action == "exception":
                    async_q.task_done()
                    try:
                        raise value
                    except ThreadedActorCancelled:
                        raise cancelled_error

    def _assign_threaded(self, queue, cancel_event_instance, message, args, kwargs):
        janus_queue.set(queue)
        assign_message.set(message)
        cancel_event.set(cancel_event_instance)
        try:
            result = self.assign(*args, **kwargs)
            queue.put(("return", result))
            queue.join()

        except Exception as e:
            logger.exception(e)
            queue.put(("exception", e))
            queue.join()

        janus_queue.set(None)
        assign_message.set(None)
        cancel_event.set(None)

    async def on_assign(self, message: Assignation):
        queue = janus.Queue()
        event = threading.Event()

        try:
            logger.info("Assigning Number two")
            print(message)
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

            threadedfut = self.loop.run_in_executor(
                self.threadpool,
                self._assign_threaded,
                queue.sync_q,
                event,
                message,
                args,
                kwargs,
            )
            queuefut = self.iterate_queue(queue.async_q, message)

            try:
                await asyncio.gather(
                    asyncio.shield(threadedfut), asyncio.shield(queuefut)
                )
                queue.close()
                await queue.wait_closed()

            except asyncio.CancelledError as e:
                await self.log("Received Cancellation for task")

                queuefut.cancel()  # We cancel the quefuture and are now only waiting for cancellation requests
                event.set()  # We are sending the request to the queue

                try:
                    await self.log("asdasdasd")
                    await queuefut
                except asyncio.CancelledError as e:
                    await self.log("Sucessfully Cancelled Thread")
                    raise e

        except asyncio.CancelledError as e:

            await self.layer.change_assignation(
                message.assignation, status=AssignationStatus.CANCELLED, message=str(e)
            )

        except Exception as e:
            await self.layer.change_assignation(
                message.assignation, status=AssignationStatus.CRITICAL, message=str(e)
            )


class FunctionalThreadedGenActor(FunctionalActor):
    def __init__(self, *args, nworkers=4, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.threadpool = ThreadPoolExecutor(nworkers)

    async def iterate_queue(self, async_q, message):
        try:
            while True:
                val = await async_q.get()
                action = val[0]
                value = val[1]

                if action == "log":
                    message = AssignLogMessage(
                        data={"message": value[0], "level": value[1]},
                        meta={**message.meta.dict(exclude={"type"})},
                    )

                    await self.transport.forward(message)
                    async_q.task_done()
                if action == "yield":
                    await self.transport.forward(
                        AssignYieldsMessage(
                            data={
                                "returns": await shrink_outputs(
                                    self.template.node,
                                    value,
                                    structure_registry=self.structure_registry,
                                )
                                if self.shrink_outputs
                                else value
                            },
                            meta={**message.meta.dict(exclude={"type"})},
                        )
                    )
                    async_q.task_done()
                if action == "done":
                    await self.transport.forward(
                        AssignDoneMessage(
                            data={}, meta={**message.meta.dict(exclude={"type"})}
                        )
                    )
                    async_q.task_done()
                    break
                if action == "exception":
                    async_q.task_done()
                    raise value

        except asyncio.CancelledError as cancelled_error:
            while True:
                val = await async_q.get()
                action = val[0]
                value = val[1]
                if action == "exception":
                    async_q.task_done()
                    try:
                        raise value
                    except ThreadedActorCancelled:
                        raise cancelled_error

    def _assign_threaded(
        self, sync_queue, cancel_event_instance, message, args, kwargs
    ):
        janus_queue.set(sync_queue)
        assign_message.set(message)
        cancel_event.set(cancel_event_instance)
        try:
            for result in self.assign(*args, **kwargs):
                sync_queue.put(("yield", result))
                sync_queue.join()

            sync_queue.put(("done", "Happy doneness"))
            sync_queue.join()

        except Exception as e:
            logger.exception(e)
            sync_queue.put(("exception", e))
            sync_queue.join()

        janus_queue.set(None)
        assign_message.set(None)
        cancel_event.set(None)

    async def on_assign(self, message):
        queue = janus.Queue()
        event = threading.Event()

        try:
            logger.info("Assigning Number two")
            args, kwargs = (
                await expand_inputs(
                    self.template.node,
                    message.data.args,
                    message.data.kwargs,
                    structure_registry=self.structure_registry,
                )
                if self.expand_inputs
                else (message.data.args, message.data.kwargs)
            )

            threadedfut = self.loop.run_in_executor(
                self.threadpool,
                self._assign_threaded,
                queue.sync_q,
                event,
                message,
                args,
                kwargs,
            )
            queuefut = self.loop.create_task(self.iterate_queue(queue.async_q, message))

            try:
                await asyncio.gather(
                    asyncio.shield(threadedfut), asyncio.shield(queuefut)
                )
                queue.close()
                await queue.wait_closed()

            except asyncio.CancelledError as e:
                await self.log("Received Cancellation for task")

                queuefut.cancel()  # We cancel the quefuture and are now only waiting for cancellation requests
                event.set()  # We are sending the request to the queue

                try:
                    await self.log("asdasdasd")
                    await queuefut
                except asyncio.CancelledError as e:
                    await self.log("Sucessfully Cancelled Thread")

                    queue.close()
                    await queue.wait_closed()

                    raise e

        except asyncio.CancelledError as e:

            await self.transport.forward(
                AssignCancelledMessage(
                    data={"canceller": str(e)},
                    meta={
                        "reference": message.meta.reference,
                        "extensions": message.meta.extensions,
                    },
                )
            )

        except Exception as e:
            logger.exception(e)
            await self.transport.forward(
                AssignCriticalMessage(
                    data={"type": e.__class__.__name__, "message": str(e)},
                    meta={
                        "reference": message.meta.reference,
                        "extensions": message.meta.extensions,
                    },
                )
            )
