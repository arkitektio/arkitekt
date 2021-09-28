import threading
from arkitekt.messages.postman.assign.assign_log import AssignLogMessage
import contextvars
from arkitekt.messages.postman.assign.assign_critical import AssignCriticalMessage
from arkitekt.messages.postman.assign.assign_cancelled import AssignCancelledMessage
from arkitekt.messages.postman.assign.assign_return import AssignReturnMessage
from arkitekt.messages.postman.assign.assign_yield import AssignYieldsMessage
from arkitekt.messages.postman.assign.assign_done import AssignDoneMessage
from arkitekt.threadvars import assign_message, transport, janus_queue
from arkitekt.messages.postman.assign.bounced_forwarded_assign import BouncedForwardedAssignMessage
from arkitekt.actors.base import Actor
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import asyncio
from arkitekt.packers.utils import shrink_inputs, shrink_outputs, expand_inputs, expand_outputs
import logging
import janus


logger = logging.getLogger(__name__)


class FunctionalActor(Actor):
    pass




class FunctionalFuncActor(FunctionalActor):
    
    async def progress(self, value, percentage):
        await self._progress(value, percentage)

    async def assign(self, *args, **kwargs):
        raise NotImplementedError("Please provide a func or overwrite the assign method!")


    async def on_assign(self, message: BouncedForwardedAssignMessage):
        try:
            logger.info("Assigning Number two")
            args, kwargs = await expand_inputs(self.template.node, message.data.args, message.data.kwargs) if self.expand_inputs else (message.data.args, message.data.kwargs)
            
            transport.set(self.transport)
            assign_message.set(message)


            returns = await self.assign(*args, **kwargs)


            assign_message.set(None)
            transport.set(None)
            await self.transport.forward(AssignReturnMessage(data={
                "returns": await shrink_outputs(self.template.node, returns) if self.shrink_outputs else returns
            }, meta = {
                "reference": message.meta.reference,
                "extensions": message.meta.extensions
            }))


        except asyncio.CancelledError as e:

            await self.transport.forward(AssignCancelledMessage(data={
                "canceller": str(e)
            }, meta = {
                "reference": message.meta.reference,
                "extensions": message.meta.extensions
            }))



        except Exception as e:
            self.console.print_exception()
            await self.transport.forward(AssignCriticalMessage(data={
                "type": e.__class__.__name__,
                "message": str(e)
            }, meta = {
                "reference": message.meta.reference,
                "extensions": message.meta.extensions
            }))




class FunctionalGenActor(FunctionalActor):

    async def assign(self, *args, **kwargs):
        raise NotImplementedError("Please provide a func or overwrite the assign method!")

    async def progress(self, value, percentage):
        await self._progress(value, percentage)

    async def on_assign(self, message: BouncedForwardedAssignMessage):
        try:
            args, kwargs = await expand_inputs(self.template.node, message.data.args, message.data.kwargs) if self.expand_inputs else (message.data.args, message.data.kwargs)
            
            transport.set(self.transport)
            assign_message.set(message)

            async for returns in self.assign(*args, **kwargs):
                await self.transport.forward(AssignYieldsMessage(data={
                    "returns": await shrink_outputs(self.template.node, returns) if self.shrink_outputs else returns
                }, meta = {
                    "reference": message.meta.reference,
                    "extensions": message.meta.extensions
                }))


            assign_message.set(None)
            transport.set(None)


            await self.transport.forward(AssignDoneMessage(data={
                "returns": await shrink_outputs(self.template.node, returns) if self.shrink_outputs else returns
            }, meta = {
                "reference": message.meta.reference,
                "extensions": message.meta.extensions
            }))


        except asyncio.CancelledError as e:

            await self.transport.forward(AssignCancelledMessage(data={
                "canceller": str(e)
            }, meta = {
                "reference": message.meta.reference,
                "extensions": message.meta.extensions
            }))



        except Exception as e:
            self.console.print_exception()
            await self.transport.forward(AssignCriticalMessage(data={
                "type": e.__class__.__name__,
                "message": str(e)
            }, meta = {
                "reference": message.meta.reference,
                "extensions": message.meta.extensions
            }))



class FunctionalThreadedFuncActor(FunctionalActor):
    nworkers = 5

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.threadpool = ThreadPoolExecutor(self.nworkers)

    def assign(self, *args, **kwargs):
        raise NotImplementedError("")


    async def iterate_queue(self, async_q, message: BouncedForwardedAssignMessage):
        while True:
            val = await async_q.get()
            action = val[0]
            value = val[1]

            if action == "log":
                message = AssignLogMessage(
                    data = {
                        "message": value[0],
                        "level": value[1]
                    },
                    meta = {**message.meta.dict(exclude={"type"})}
                )

                await self.transport.forward(message)
                async_q.task_done()
            if action == "return":
                await self.transport.forward(AssignReturnMessage(data={
                    "returns": await shrink_outputs(self.template.node, value) if self.shrink_outputs else value
                }, meta = {**message.meta.dict(exclude={"type"})}
                ))
                async_q.task_done()
                break
            if action == "exception":
                await self.transport.forward(AssignCriticalMessage(data={
                        "type": val.__class__.__name__,
                        "message": str(val)
                    }, meta = {**message.meta.dict(exclude={"type"})}
                    ))
                async_q.task_done()
                break  



    def _assign_threaded(self, queue, message, args, kwargs):
        janus_queue.set(queue)
        assign_message.set(message)
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


    async def on_assign(self, message: BouncedForwardedAssignMessage):
        queue = janus.Queue()

        try:
            logger.info("Assigning Number two")
            args, kwargs = await expand_inputs(self.template.node, message.data.args, message.data.kwargs) if self.expand_inputs else (message.data.args, message.data.kwargs)
            

            threadedfut = self.loop.run_in_executor(self.threadpool, self._assign_threaded,  queue.sync_q, message, args, kwargs)
            queuefut =  self.iterate_queue(queue.async_q, message)

            try:
                await asyncio.gather(threadedfut, queuefut)
                queue.close()
                await queue.wait_closed()

            except asyncio.CancelledError as e:
                await self.log("Received Cancellation for task")

                if not threadedfut.done():
                    await self.log("Sending request to Queue To Cancell")
                    threadedfut.cancel()

                try:
                    await threadedfut
                except asyncio.CancelledError as e:
                    await self.log("Sucessfully Cancelled Thread")
                    raise e

        except asyncio.CancelledError as e:

            await self.transport.forward(AssignCancelledMessage(data={
                "canceller": str(e)
            }, meta = {
                "reference": message.meta.reference,
                "extensions": message.meta.extensions
            }))



        except Exception as e:
            self.console.print_exception()
            await self.transport.forward(AssignCriticalMessage(data={
                "type": e.__class__.__name__,
                "message": str(e)
            }, meta = {
                "reference": message.meta.reference,
                "extensions": message.meta.extensions
            }))




class FunctionalThreadedGenActor(FunctionalActor):
    nworkers = 5

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.threadpool = ThreadPoolExecutor(self.nworkers)

    def assign(self, *args, **kwargs):
        raise NotImplementedError("")  

    
    async def iterate_queue(self, async_q, message: BouncedForwardedAssignMessage):
        while True:
            val = await async_q.get()
            action = val[0]
            value = val[1]

            if action == "log":
                message = AssignLogMessage(
                    data = {
                        "message": value[0],
                        "level": value[1]
                    },
                    meta = {**message.meta.dict(exclude={"type"})}
                )

                await self.transport.forward(message)
                async_q.task_done()
            if action == "yield":
                await self.transport.forward(AssignYieldsMessage(data={
                    "returns": await shrink_outputs(self.template.node, value) if self.shrink_outputs else value
                }, meta = {**message.meta.dict(exclude={"type"})}
                ))
                async_q.task_done()
            if action == "done":
                await self.transport.forward(AssignDoneMessage(data={
                }, meta = {**message.meta.dict(exclude={"type"})}
                ))
                async_q.task_done()
            if action == "exception":
                await self.transport.forward(AssignCriticalMessage(data={
                        "type": val.__class__.__name__,
                        "message": str(val)
                    }, meta = {**message.meta.dict(exclude={"type"})}
                    ))
                async_q.task_done()
                break  



    def _assign_threaded(self, queue, cancel_event, message, args, kwargs):
        janus_queue.set(queue)
        assign_message.set(message)
        try:
            if cancel_event.is_set(): 
                queue.put(("cancelled", "Cancelled before iteration"))
                queue.join()
                return

            iteration = 0
            for result in self.assign(*args, **kwargs):
                if cancel_event.is_set():
                    queue.put(("cancelled",f"Cancelled after {iteration} Iterations"))
                    queue.join()
                    return

                queue.put(("yield", result))
                queue.join()

            queue.put(("done","Happy doneness"))

        except Exception as e:
            logger.exception(e)
            queue.put(("exception", e))

        janus_queue.set(None)
        assign_message.set(None) 



    async def on_assign(self, message: BouncedForwardedAssignMessage):
        queue = janus.Queue()
        event = threading.Event()
        
        try:
            logger.info("Assigning Number two")
            args, kwargs = await expand_inputs(self.template.node, message.data.args, message.data.kwargs) if self.expand_inputs else (message.data.args, message.data.kwargs)
            

            threadedfut = self.loop.run_in_executor(self.threadpool, self._assign_threaded,  queue.sync_q, event, message, args, kwargs)
            queuefut =  self.iterate_queue(queue.async_q, message)

            try:
                await asyncio.gather(threadedfut, queuefut)
                queue.close()
                await queue.wait_closed()

            except asyncio.CancelledError as e:
                await self.log("Received Cancellation for task")

                if not threadedfut.done():
                    await self.log("Sending request to Queue To Cancell")
                    threadedfut.cancel()

                try:
                    await threadedfut
                except asyncio.CancelledError as e:
                    await self.log("Sucessfully Cancelled Thread")
                    raise e

        except asyncio.CancelledError as e:

            await self.transport.forward(AssignCancelledMessage(data={
                "canceller": str(e)
            }, meta = {
                "reference": message.meta.reference,
                "extensions": message.meta.extensions
            }))



        except Exception as e:
            self.console.print_exception()
            await self.transport.forward(AssignCriticalMessage(data={
                "type": e.__class__.__name__,
                "message": str(e)
            }, meta = {
                "reference": message.meta.reference,
                "extensions": message.meta.extensions
            }))
