
from arkitekt.actors.functional import FunctionalFuncActor
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
from koil.koil import Koil
from koil.qt import FutureWrapper, TimeoutFutureWrapper

logger = logging.getLogger(__name__)





class ActorSignals(QObject):

        def __init__(self, timeout=300) -> None:
            self.assign = TimeoutFutureWrapper(timeout=timeout)
            self.on_provide = TimeoutFutureWrapper(timeout=timeout, pass_through=True)
            self.on_unprovide = TimeoutFutureWrapper(timeout=timeout, pass_through=True)


class QtActor(FunctionalFuncActor, QObject):

    def __init__(self, *args,  qt_assign=None, loop= None, qt_on_provide = None, qt_on_unprovide = None, timeout=300, koil: Koil = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.koil = koil or get_current_koil()
        self.loop = self.koil.loop

        self.qt_assign = qt_assign
        self.qt_on_provide = qt_on_provide
        self.qt_on_unprovide = qt_on_unprovide

        self.signals = ActorSignals()

        if self.qt_assign is not None:
            self.signals.assign.call.connect(self.assign_function_in_qtloop) # insignal will be set dymaically by qt agent

        if self.qt_on_provide is not None:
            self.signals.on_provide.connect(self.provide_function_in_qtloop)

        if self.qt_on_unprovide is not None:
            self.signals.on_unprovide.connect(self.unprovide_function_in_qtloop)

        

    def provide_function_in_qtloop(self, reference, args, kwargs):
        try:
            returns = self.qt_on_provide(*args, **kwargs) if self.qt_on_provide else None
            self.signals.on_provide.resolve.emit(reference, returns)
        except Exception as e:
            self.signals.on_provide.reject.emit(reference, e)

    def unprovide_function_in_qtloop(self, reference, args, kwargs):
        try:
            returns = self.qt_on_unprovide(*args, **kwargs) if self.qt_on_unprovide else None
            self.signals.on_unprovide.resolve.emit(reference, returns)
        except Exception as e:
            self.signals.on_unprovide.reject.emit(reference, e)


    def assign_function_in_qtloop(self, reference, args, kwargs):
        try:
            returns = self.qt_assign(*args, **kwargs)
            self.signals.assign.resolve.emit(reference, returns)
        except Exception as e:
            self.signals.assign.reject.emit(reference, e)


    async def assign(self, *args, **kwargs):
        print("Calledsssssss")
        await self.signals.assign.acall(*args, **kwargs)

    async def on_provide(self, *args, **kwargs):
        print("Calledssssss2e23e2e1s")
        await self.signals.on_provide.acall(*args, **kwargs)

    async def on_unprovide(self, *args, **kwargs):
        print("Calledssssdsdsdssss")
        await self.signals.on_unprovide.acall(*args, **kwargs)


    

