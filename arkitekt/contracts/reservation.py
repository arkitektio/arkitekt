from arkitekt.monitor.monitor import get_current_monitor
from herre.console.context import get_current_console
from uuid import uuid4
from herre.auth import get_current_herre
from arkitekt.packers.utils import expand_outputs, shrink_inputs
from asyncio.futures import Future
from arkitekt.messages.postman.log import LogLevel
from contextvars import Context
from arkitekt.messages.postman.reserve.reserve_transition import ReserveState
from arkitekt.contracts.exceptions import AssignmentException
from arkitekt.messages import *
from arkitekt.schema.enums import NodeType
from arkitekt.messages.postman.reserve.params import ReserveParams
from rich.table import Table
from rich.panel import Panel
from arkitekt.monitor import Monitor, current_monitor
from arkitekt.registry import get_current_rpc
import asyncio
import logging

logger = logging.getLogger(__name__)

class UnknownMessageError(Exception):
    pass


class ReservationError(Exception):
    pass


class CouldNotReserveError(ReservationError):
    pass


class IncorrectStateForAssignation(ReservationError):
    pass


def build_reserve_message(reference, node_id: str = None, template_id: str= None, provision: str= None, params_dict: dict = {}, with_log=False, context=None):
    assert reference is not None, "Must have a reference"
    assert node_id is not None or template_id is not None, "Please provide either a node_id or template_id"

    data={
                                "node": node_id, 
                                "template": template_id, 
                                "provision": provision,
                                "params": params_dict,
    }
    meta={
        "reference": reference,
        "extensions": {
            "with_progress": with_log,
        }
    }

    if context:
        meta = {**meta, "context": context}
        return BouncedReserveMessage(data=data, meta=meta)

    else:
        return ReserveMessage(data=data, meta=meta)

def build_unreserve_messsage(reference, reservation, with_log=False, context=None):
    assert reference is not None, "Must have a reference"
    data= {
                                        "reservation": reservation
    }
    
    meta={
                                    "reference": reference, 
                                    "extensions": {
                                        "with_progress": with_log
                                    }
    }

    if context:
        meta = {**meta, "context": context}
        return BouncedUnreserveMessage(data=data, meta=meta)

    else:
        return UnreserveMessage(data=data, meta=meta)

def build_assign_message(reference, reservation, args, kwargs, with_log=False, context=None, persist=False):
    assert reference is not None, "Must have a reference"

    data = {
                                    "reservation": reservation,
                                    "args": args, 
                                    "kwargs": kwargs,
    }

    meta = {
                                    "reference": reference, 
                                    "extensions": {
                                        "with_progress": with_log,
                                        "persist": persist
                                    }
    }

    if context:
        meta = {**meta, "context": context}
        return BouncedAssignMessage(data=data, meta=meta)

    else:
        return AssignMessage(data=data, meta=meta)

def build_unassign_messsage(reference, assignation, with_log=False, context=None, persist=False):
    assert reference is not None, "Must have a reference"
    data= {
                                        "assignation": assignation
    }
                                    
    meta={
                                    "reference": reference, 
                                    "extensions": {
                                        "with_progress": with_log,
                                        "persist": persist
                                    }
    }

    if context:
        meta = {**meta, "context": context}
        return BouncedUnassignMessage(data=data, meta=meta)

    else:
        return UnassignMessage(data=data, meta=meta)


class Reservation:

    def __init__(self, node,
        reference: str = None,
        provision: str = None, 
        monitor: Monitor = None,
        ignore_node_exceptions=False,
        transition_hook=None,
        with_log=False,
        enter_on=[ReserveState.ACTIVE], 
        exit_on=[ReserveState.ERROR, ReserveState.CANCELLED],
        context: Context =None,
        loop=None,
         **params) -> None:

        self.monitor: Monitor = monitor or get_current_monitor()
        self.panel = self.monitor.create_reservation_panel(self) if self.monitor else None


        self.console = get_current_console()

        self.herre = get_current_herre()
        self.loop = loop or self.herre.loop
        self.rpc = get_current_rpc(force_creation=True)
        
        assert "can_assign" in self.herre.grant.scopes, "Cannot assign to nodes if can_assign is not in scopes"

        # Reservation Params
        self.reference = reference or str(uuid.uuid4())
        self.provision = provision
        self.node = node
        self.params = ReserveParams(**params)
        self.with_log = with_log or (self.monitor.log if self.monitor else None)


        self.context = context # with_bounced allows us forward bounced checks
        if self.context:
            assert "can_forward_bounce" in self.herre.grant.scopes, "In order to use with_bounced forwarding you need to have the can_forward_bounced scope"

        # Exception Mangement
        self.ignore_node_exceptions = ignore_node_exceptions
        self.critical_error = None

        # State management
        self.transition_hook = transition_hook
        assert self.transition_hook is None or asyncio.iscoroutinefunction(self.transition_hook), "Transition Hook must be either a coroutine or set to None"
        self.exit_states = exit_on
        self.enter_states = enter_on
        self.current_state = ReserveState.STARTING



    
    def log(self, message: str, level: LogLevel=LogLevel.DEBUG):
        """Logs a Message

        The Logged Message will be display on the Monitor if running inside a Monitor
        and send to the logging output.

        Args:
            message (str): The Message
            level (LogLevel, optional): The LogLevel. Defaults to LogLevel.DEBUG.
        """
        if self.panel:
            self.panel.log(message, level=level)
        logger.info(f"{level}: {message}")


    async def transition_state(self, message: ReserveTransitionMessage):
        # Once we acquire a reserved resource our contract (the inner part of the context can start)
        if self.transition_hook: await self.transition_hook(self, message.data.state)
        
        if message.data.state in self.exit_states:

            if self.enter_future.done():
                self.log(f"We have transitioned to a critical State {message.data.message}. Terminating on Next Call")
            else:
                self.log("Cancelling Reservation")
                self.enter_future.set_exception(Exception(message.data.message))

            if not self.is_closing: 
                self.log(f"Received Exitstate: {message.data.state}. Closing reservation at next assignment", level=LogLevel.CRITICAL)
            

        if message.data.state in self.enter_states:
            if self.enter_future.done():
                logger.info("We are already entered.")
            else:
                self.enter_future.set_result(message.meta.reference)


        self.old_state = self.current_state
        self.current_state = message.data.state
        self.log(f"[red] {self.old_state} > {self.current_state}: {message.data.message}", LogLevel.INFO)


    async def assign_async(self, *args, bypass_shrink=False, bypass_expand=False, persist=True, with_log=True, context=None, raise_node_exceptions=True, **kwargs):
        logger.info(f"Assigning {args} {kwargs} ")
        assert self.node.type == NodeType.FUNCTION, "You cannot assign to a Generator Node, use the stream Method!"

        if self.current_state in self.exit_states:
            raise IncorrectStateForAssignation(f"Current State {self.current_state} is an Element of Exit States {self.exit_states}")
        

        
        shrinked_args, shrinked_kwargs = await shrink_inputs(self.node, *args, **kwargs) if not bypass_shrink else (args, kwargs)
        


        context = context or self.context
        assign_reference = str(uuid.uuid4())
        assign_message = build_assign_message(assign_reference, self.reference, shrinked_args, shrinked_kwargs, with_log=with_log, context=context)
        assignation_queue = await self.rpc.stream_replies_to_queue(assign_message)

        try:
            while True:
                message = await assignation_queue.get()

                if self.current_state in self.exit_states:
                    raise IncorrectStateForAssignation(f"Current State {self.current_state} is an Element of Exit States {self.exit_states}")

                if isinstance(message, AssignReturnMessage):
                    return await expand_outputs(self.node, message.data.returns) if not bypass_expand else message.data.returns    

                if isinstance(message, AssignCancelledMessage):
                    raise AssignmentException(f"Assignment was cancelled from a different Agent: ID: {message.data.canceller}")

                if isinstance(message, AssignLogMessage):
                    self.log(message.data.message, message.data.level)
                    continue

                if isinstance(message, AssignCriticalMessage):
                    if raise_node_exceptions:
                        raise AssignmentException(message.data.message)
                    else:
                        self.log(message.data.message, LogLevel.CRITICAL)

                if isinstance(message, AssignYieldsMessage):
                    raise AssignmentException("Received a Yield from a Node that should never yield! CRITICAL PROTOCOL EXCEPTION")

                raise UnknownMessageError(message)


        except asyncio.CancelledError as e:
            self.log("Assigment Required Cancellation", level=LogLevel.INFO)

            un_assign_reference = str(uuid.uuid4())
            unassign_message = build_unassign_messsage(un_assign_reference, assign_reference, context=context)
            

            self.log(f"Cancellation Condition {unassign_message}")
            await self.rpc.transport.forward(unassign_message)

            while True:
                message = await assignation_queue.get()
                if isinstance(message, AssignCancelledMessage):

                    if message.data.canceller != un_assign_reference:
                        self.log("Canceller does not match our Cancellation Request, Race Condition?")
                    raise e

                else:
                    print("Raced Condition",message)



    async def stream_async(self, *args, bypass_shrink=False, bypass_expand=False, persist=True, context=None, with_log=True, **kwargs):
        assert self.node.type == NodeType.GENERATOR, "You cannot stream a Function Node, use the assign Method!"

        if self.current_state in self.exit_states:
            raise IncorrectStateForAssignation(f"Current State {self.current_state} is an Element of Exit States {self.exit_states}")

        shrinked_args, shrinked_kwargs = await shrink_inputs(self.node, *args, **kwargs) if not bypass_shrink else (args, kwargs)
        
        context = context or self.context
        assign_reference = str(uuid.uuid4())
        assign_message = build_assign_message(assign_reference, self.reference, shrinked_args, shrinked_kwargs, with_log=with_log, context=context)
        assignation_queue = await self.rpc.stream_replies_to_queue(assign_message)

        try:
            while True:
                message = await assignation_queue.get()

                if isinstance(message, AssignYieldsMessage):
                    yield await expand_outputs(self.node, message.data.returns) if not bypass_expand else message.data.returns    

                elif isinstance(message, AssignDoneMessage):   
                    break

                elif isinstance(message, AssignCancelledMessage):
                    raise AssignmentException(f"Assignment was cancelled from a different Agent: ID: {message.data.canceller}")

                elif isinstance(message, AssignLogMessage):
                    self.log(message.data.message, message.data.level)

                elif isinstance(message, AssignCriticalMessage):
                    raise AssignmentException(message.data.message)

                elif isinstance(message, AssignReturnMessage):
                    raise AssignmentException("Received a Return from a Node that should never return! CRITICAL PROTOCOL EXCEPTION")

                else:
                    raise UnknownMessageError(message)


        except asyncio.CancelledError as e:
            self.log("Assigment Required Cancellation", level=LogLevel.INFO)

            un_assign_reference = str(uuid.uuid4())
            unassign_message = build_unassign_messsage(un_assign_reference, assign_reference, context=context)
            
            await self.rpc.transport.forward(unassign_message)


            while True:
                message = await assignation_queue.get()

                if isinstance(message, AssignCancelledMessage):

                    if message.data.canceller != un_assign_reference:
                        self.log("Canceller does not match our Cancellation Request, Race Condition?")
                    raise e

                else:
                    logger.info(f"Wrong message for cancellation {message}")



    async def stream_worker(self):

        reserve_message = build_reserve_message(reference=self.reference, node_id=self.node.id, params_dict=self.params.dict())
        reservation_queue = await self.rpc.stream_replies_to_queue(reserve_message)

        try:
            while True: 
                message = await reservation_queue.get()

                if isinstance(message, ReserveLogMessage):
                    self.log(message.data.message, message.data.level)


                elif isinstance(message, ProvideTransitionMessage):
                    self.log(message.data.message, message.data.state)
                

                elif isinstance(message, ReserveTransitionMessage):
                    
                        await self.transition_state(message)

                else:
                    self.enter_future.set_exception(UnknownMessageError("Received Unnown Message"))

                reservation_queue.task_done()

        except asyncio.CancelledError as e:

            unreserve_reference = str(uuid.uuid4())
            unreserve_message = build_unreserve_messsage(unreserve_reference, self.reference,  context=self.context)
            
            await self.rpc.transport.forward(unreserve_message)


            while True:
                message = await reservation_queue.get()

                if isinstance(message, ReserveTransitionMessage):
                    if self.transition_hook: await self.transition_hook(self, message.data.state)
                    if message.data.state in [ReserveState.CANCELLED]:
                        raise e
                    else:
                        self.console.log(f"[red] Received Completely Different State {message.data.state}")

                else:
                    self.console.log(f"[red] Received Completely Different Message {message}")

        
        except Exception as e: 
            self.console.print_exception()
            if not self.enter_future.done():
                self.enter_future.set_exception(e)
            raise e


    async def cancel(self):
        self.is_closing = True
        self.stream_task.cancel()
        try:
            await self.stream_task
        except asyncio.CancelledError as e:
            pass

    async def start(self):
        return await self.__aenter__()

    async def end(self, timeout=3):
        #TODO: implement timeout
        await self.cancel()

    async def __aenter__(self):
        if self.panel: self.panel.start()

        # Check connection level
        if not self.rpc.connected:
            await self.rpc.connect()

        self.is_closing = False
        
        self.enter_future = self.loop.create_future()
        self.stream_task = self.loop.create_task(self.stream_worker())

        try:
            self.enter_state = await self.enter_future
            return self

        except Exception as e:
            raise CouldNotReserveError(f"Could not Reserve Reservation {self.reference} for Node {self.node}") from e


    async def __aexit__(self, type, value, traceback):

        await self.cancel()
        if self.panel: self.panel.end()
        
        if type is not None:
            if issubclass(type, asyncio.CancelledError): 
                print("Raising cancellation")
                raise type(value).with_traceback(traceback)

            if issubclass(type, Exception):
                print(f"Raising exceütopm {type} {value} {traceback}")
                raise type(value).with_traceback(traceback)


            raise type(value).with_traceback(traceback)


    def stream(self, *args, bypass_shrink=False, bypass_expand=False, persist=True, **kwargs):
        return self.stream_async(*args, bypass_shrink=bypass_shrink, bypass_expand=bypass_expand, persist=persist, **kwargs)

        
    def assign(self, *args, bypass_shrink=False, bypass_expand=False, persist=True, **kwargs):
        return self.assign_async(*args, bypass_shrink=bypass_shrink, bypass_expand=bypass_expand, persist=persist, **kwargs)




    




       