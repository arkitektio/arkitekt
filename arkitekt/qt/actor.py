from arkitekt.actors.functional import FunctionalFuncActor
import logging
from koil.koil import Koil
from koil.qt import TimeoutFutureWrapper
from qtpy.QtCore import QObject


logger = logging.getLogger(__name__)


class ActorSignals(QObject):
    def __init__(self, timeout=300) -> None:
        self.assign = TimeoutFutureWrapper(timeout=timeout)
        self.on_provide = TimeoutFutureWrapper(timeout=timeout, pass_through=True)
        self.on_unprovide = TimeoutFutureWrapper(timeout=timeout, pass_through=True)


class QtActor(FunctionalFuncActor, QObject):
    def __init__(
        self,
        *args,
        qt_assign=None,
        qt_on_provide=None,
        qt_on_unprovide=None,
        timeout=300,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)

        self.qt_assign = qt_assign
        self.qt_on_provide = qt_on_provide
        self.qt_on_unprovide = qt_on_unprovide

        self.signals = ActorSignals()

        if self.qt_assign is not None:
            self.signals.assign.wire(
                self.assign_function_in_qtloop
            )  # insignal will be set dymaically by qt agent

        if self.qt_on_provide is not None:
            self.signals.on_provide.wire(self.provide_function_in_qtloop)

        if self.qt_on_unprovide is not None:
            self.signals.on_unprovide.wire(self.unprovide_function_in_qtloop)

    def provide_function_in_qtloop(self, reference, args, kwargs):
        try:
            returns = (
                self.qt_on_provide(*args, **kwargs) if self.qt_on_provide else None
            )
            self.signals.on_provide.resolve(reference, returns)
        except Exception as e:
            self.signals.on_provide.reject(reference, e)

    def unprovide_function_in_qtloop(self, reference, args, kwargs):
        try:
            returns = (
                self.qt_on_unprovide(*args, **kwargs) if self.qt_on_unprovide else None
            )
            self.signals.on_unprovide.resolve(reference, returns)
        except Exception as e:
            self.signals.on_unprovide.reject(reference, e)

    def assign_function_in_qtloop(self, reference, args, kwargs):
        try:
            returns = self.qt_assign(*args, **kwargs)
            self.signals.assign.resolve(reference, returns)
        except Exception as e:
            self.signals.assign.reject(reference, e)

    async def assign(self, *args, **kwargs):
        return await self.signals.assign.acall(*args, **kwargs)

    async def on_provide(self, *args, **kwargs):
        return await self.signals.on_provide.acall(*args, **kwargs)

    async def on_unprovide(self, *args, **kwargs):
        return await self.signals.on_unprovide.acall(*args, **kwargs)
