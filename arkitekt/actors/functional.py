import contextvars
from arkitekt.messages.postman.assign.assign_critical import AssignCriticalMessage
from arkitekt.messages.postman.assign.assign_cancelled import AssignCancelledMessage
from arkitekt.messages.postman.assign.assign_return import AssignReturnMessage
from arkitekt.messages.postman.assign.assign_yield import AssignYieldsMessage
from arkitekt.messages.postman.assign.assign_done import AssignDoneMessage
from arkitekt.threadvars import assign_message, transport
from arkitekt.messages.postman.assign.bounced_forwarded_assign import BouncedForwardedAssignMessage
from arkitekt.actors.base import Actor
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import asyncio
from arkitekt.packers.utils import shrink_inputs, shrink_outputs, expand_inputs, expand_outputs
import logging

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




class FunctionalThreadedGenActor(FunctionalActor):
    nworkers = 5

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.threadpool = ThreadPoolExecutor(self.nworkers)

    def assign(self, *args, **kwargs):
        raise NotImplementedError("")  