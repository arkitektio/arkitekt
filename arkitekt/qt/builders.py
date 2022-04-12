from typing import Any
from qtpy import QtCore
from arkitekt.agents.transport.base import AgentTransport
from arkitekt.messages import Provision
from koil.qt import QtCoro
from arkitekt.actors.functional import FunctionalFuncActor
from arkitekt.actors.builder import ActorBuilder


class QtInLoopBuilder(QtCore.QObject, ActorBuilder):
    """A function that takes a provision and an agent and returns an actor.

    The actor produces by this builder will be running in the same thread as the
    koil instance (aka, the thread that called the builder).

    Args:
        QtCore (_type_): _description_
    """

    def __init__(self, assign=None, *args, parent=None, **actor_kwargs) -> None:
        super().__init__(*args, parent=parent)
        self.coro = QtCoro(
            lambda f, *args, **kwargs: assign(*args, **kwargs), autoresolve=True
        )
        self.provisions = {}
        self.actor_kwargs = actor_kwargs

    async def on_assign(self, *args, **kwargs) -> None:
        return await self.coro.acall(*args)

    def build_actor(self, provision: Provision, transport: AgentTransport) -> Any:
        try:
            ac = FunctionalFuncActor(
                provision=provision,
                transport=transport,
                assign=self.on_assign,
                **self.actor_kwargs
            )
            return ac
        except Exception as e:
            raise e
