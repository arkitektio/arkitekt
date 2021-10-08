
from herre.herre import get_current_herre
from arkitekt.threadvars import get_current_assign
from qtpy.QtCore import QObject, Signal
from arkitekt.messages.postman.assign.assign_cancelled import AssignCancelledMessage
from arkitekt.messages.postman.unassign.bounced_forwarded_unassign import BouncedForwardedUnassignMessage
from arkitekt.messages.postman.provide.provide_transition import ProvideState, ProvideTransitionMessage
from arkitekt.messages.postman.assign.assign_log import AssignLogMessage
from arkitekt.messages.postman.assign.assign_critical import AssignCriticalMessage
from arkitekt.messages.postman.assign.bounced_forwarded_assign import BouncedForwardedAssignMessage
from arkitekt.messages.postman.assign.bounced_assign import BouncedAssignMessage
from arkitekt.messages.postman.provide.provide_critical import ProvideCriticalMessage
from arkitekt.messages.postman.log import LogLevel
from arkitekt.messages.postman.provide.provide_log import ProvideLogMessage
import asyncio
from herre.wards.base import WardException
from arkitekt.actors.actify import actify, define
from arkitekt.actors.base import Actor
from arkitekt.messages.postman.unprovide.bounced_unprovide import BouncedUnprovideMessage
from arkitekt.messages.base import MessageDataModel, MessageModel
from arkitekt.messages.postman.provide.bounced_provide import BouncedProvideMessage
from arkitekt.schema.template import Template
from arkitekt.schema.node import Node
from arkitekt.packers.transpilers import Transpiler
from typing import Callable, Dict, List, Tuple, Type
from arkitekt.agents.base import Agent, AgentException, parse_params
import logging
from herre.console import get_current_console
import uuid
from koil import get_current_koil

logger = logging.getLogger(__name__)


class ActorSignals():

    def __init__(self, assigns, cancels, returns, excepts) -> None:
        self.assigns = assigns # Connectable
        self.cancels = cancels
        self.returns = returns # Emitable
        self.excepts = excepts





class QtActor(QObject):
    provideInSignal = Signal(str, BouncedProvideMessage)
    provideOutSignal = Signal(str)
    provideErrorSignal = Signal(str, Exception)

    assignInSignal = Signal(str,tuple, dict)
    assignOutSignal =  Signal(str, tuple)
    assignErrorSignal = Signal(str, Exception)

    unprovideInSignal = Signal(str, BouncedProvideMessage)
    unprovideOutSignal = Signal(str)
    unprovideErrorSignal = Signal(str, Exception)

    def __init__(self, *args,  qt_assign=None, loop= None, qt_on_provide = None, qt_on_unprovide = None, timeout=300, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.futureMap = {}
        self.koil = get_current_koil()
        self.loop = loop or self.koil.loop

        self.assign_timeout = timeout
        self.provide_timeout = timeout
        self.unprovide_timeout = timeout

        self.signals = ActorSignals(self.assignInSignal, None, self.assignOutSignal, self.assignErrorSignal)


        if qt_assign is not None:

            self.qt_assign = qt_assign
            self.assignInSignal.connect(self.assign_function_in_qtloop) # insignal will be set dymaically by qt agent
            self.assignOutSignal.connect(self.set_assign_future_qtloop)
            self.assignErrorSignal.connect(self.set_error_future_qtloop)

        if qt_on_provide is not None:
            self.qt_on_provide = qt_on_provide
            self.provideInSignal.connect(self.provide_function_in_qtloop)
            self.provideOutSignal.connect(self.set_provide_future_qtloop)
            self.provideErrorSignal.connect(self.set_error_future_qtloop)

        if qt_on_unprovide is not None:
            self.qt_on_unprovide = qt_on_unprovide
            self.unprovideInSignal.connect(self.unprovide_function_in_qtloop)
            self.unprovideOutSignal.connect(self.set_unprovide_future_qtloop)
            self.unprovideErrorSignal.connect(self.set_error_future_qtloop)



        

    def provide_function_in_qtloop(self, reference, *args, **kwargs):
        try:
            returns = self.qt_on_provide(*args, **kwargs) if self.qt_on_provide else None
            self.provideOutSignal.emit(reference)
        except Exception as e:
            self.provideErrorSignal.emit(reference, e)

    def unprovide_function_in_qtloop(self, reference, *args, **kwargs):
        try:
            returns = self.qt_on_unprovide(*args, **kwargs) if self.qt_on_unprovide else None
            self.unprovideOutSignal.emit(reference)
        except Exception as e:
            self.unprovideErrorSignal.emit(reference, e)

    def set_provide_future_qtloop(self, reference):
        self.loop.call_soon_threadsafe(self.futureMap[reference].set_result, None)

    def set_unprovide_future_qtloop(self, reference):
        self.loop.call_soon_threadsafe(self.futureMap[reference].set_result, None)
    
    def set_assign_future_qtloop(self, reference, returns):
        if len(returns) == 1:
            print("Setting None")
            self.loop.call_soon_threadsafe(self.futureMap[reference].set_result, returns[0])
        if len(returns) >= 2:
            print("Setting Result")
            self.loop.call_soon_threadsafe(self.futureMap[reference].set_result, returns)


    def assign_function_in_qtloop(self, reference, args, kwargs):
        try:
            returns = self.qt_assign(*args, **kwargs)
            if isinstance(returns, tuple):
                self.assignOutSignal.emit(reference, returns)
            else:
                self.assignOutSignal.emit(reference, (returns,))
        except Exception as e:
            self.assignErrorSignal.emit(reference, e)


    def set_error_future_qtloop(self, reference, exception):
        self.loop.call_soon_threadsafe(self.futureMap[reference].set_exception, exception)
    

    async def on_provide(self, message):
        print(self, message)
        reference = str(uuid.uuid4())
        future = self.loop.create_future()
        self.futureMap[reference] = future
        self.provideInSignal.emit(reference, message)
        return await asyncio.wait_for(future, timeout=self.provide_timeout)

    async def on_unprovide(self,message):
        reference = str(uuid.uuid4())
        future = self.loop.create_future()
        self.futureMap[reference] = future
        self.unprovideInSignal.emit(reference,message)
        return await asyncio.wait_for(future, timeout=self.unprovide_timeout)

    async def assign(self, *args, **kwargs):
        reference = str(uuid.uuid4())
        future = self.loop.create_future()
        self.futureMap[reference] = future
        self.assignInSignal.emit(reference, args, kwargs)

        return await asyncio.wait_for(future, timeout=self.assign_timeout)




