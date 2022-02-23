import threading
from typing import Any, Coroutine, Dict, List
from arkitekt.actors.errors import ThreadedActorCancelled
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
        print("Assignation BITIIICH")
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

            await self.transport.change_assignation(
                assignation.assignation,
                status=AssignationStatus.ASSIGNED,
            )

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
                returns=returns,
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
            print(e)
            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.CRITICAL, message=repr(e)
            )

            raise e


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
                    raise NotImplementedError("Logging does not work right now")
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

                    await self.transport.change_assignation(
                        message.assignation,
                        status=AssignationStatus.RETURNED,
                        resulsts=returns,
                    )
                    async_q.task_done()
                    break
                if action == "exception":
                    async_q.task_done()
                    raise value

        except asyncio.CancelledError as e:
            logger.info(f"Received Cancellation to iterate over async queue")
            while True:
                val = await async_q.get()
                action = val[0]
                value = val[1]
                if action == "exception":
                    async_q.task_done()
                    try:
                        raise value  # Lets try to raise the exception
                    except ThreadedActorCancelled:
                        raise e

    def _assign_threaded(
        self,
        queue: janus._SyncQueueProxy,
        cancel_event_instance: threading.Event,
        message: Assignation,
        args: List[Any],
        kwargs: Dict[str, Any],
    ):
        current_janus_queue.set(queue)
        current_assignation.set(message)
        current_cancel_event.set(cancel_event_instance)
        try:
            result = self.assign(*args, **kwargs)
            queue.put(("return", result))
            queue.join()

        except Exception as e:
            queue.put(("exception", e))
            queue.join()

        current_janus_queue.set(None)
        current_assignation.set(None)
        current_cancel_event.set(None)

    async def on_assign(self, message: Assignation):
        loop = asyncio.get_event_loop()
        queue = janus.Queue()
        event = threading.Event()

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

            threadedfut = loop.run_in_executor(
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

                queuefut.cancel()  # We cancel the quefuture and are now only waiting for cancellation requests
                event.set()  # We are sending the request to the queue

                try:
                    await queuefut
                except asyncio.CancelledError as e:
                    raise e

        except asyncio.CancelledError as e:

            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.CANCELLED, message=str(e)
            )

        except Exception as e:
            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.CRITICAL, message=str(e)
            )


class FunctionalThreadedGenActor(FunctionalActor):
    def __init__(self, *args, nworkers=4, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.threadpool = ThreadPoolExecutor(nworkers)

    async def iterate_queue(
        self, async_q: janus._AsyncQueueProxy, message: Assignation
    ):
        try:
            while True:
                val = await async_q.get()
                action = val[0]
                value = val[1]

                if action == "log":
                    raise NotImplementedError("Logging does not work right now")
                    async_q.task_done()
                if action == "yield":

                    returns = (
                        await shrink_outputs(
                            self.template.node,
                            value,
                            structure_registry=self.structure_registry,
                        )
                        if self.shrink_outputs
                        else value
                    )

                    await self.transport.change_assignation(
                        message.assignation,
                        status=AssignationStatus.YIELD,
                        returns=returns,
                    )
                    async_q.task_done()
                if action == "done":
                    await self.transport.change_assignation(
                        message.assignation,
                        status=AssignationStatus.DONE,
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
        self,
        queue: janus._SyncQueueProxy,
        cancel_event_instance: threading.Event,
        message: Assignation,
        args: List[Any],
        kwargs: Dict[str, Any],
    ):
        current_janus_queue.set(queue)
        current_assignation.set(message)
        current_cancel_event.set(cancel_event_instance)
        try:
            for result in self.assign(*args, **kwargs):
                queue.put(("yield", result))
                queue.join()

            queue.put(("done", "Happy doneness"))
            queue.join()

        except Exception as e:
            logger.exception(e)
            queue.put(("exception", e))
            queue.join()

        current_janus_queue.set(None)
        current_assignation.set(None)
        current_cancel_event.set(None)

    async def on_assign(self, message: Assignation):
        loop = asyncio.get_event_loop()
        queue = janus.Queue()
        event = threading.Event()

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

            threadedfut = loop.run_in_executor(
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

                queuefut.cancel()  # We cancel the quefuture and are now only waiting for cancellation requests
                event.set()  # We are sending the request to the queue

                try:
                    await queuefut
                except asyncio.CancelledError as e:
                    raise e

        except asyncio.CancelledError as e:

            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.CANCELLED, message=str(e)
            )

        except Exception as e:
            await self.transport.change_assignation(
                message.assignation, status=AssignationStatus.CRITICAL, message=str(e)
            )
