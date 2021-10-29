from abc import abstractmethod
from arkitekt.agents.base import Agent
from arkitekt.messages.postman.assign.bounced_forwarded_assign import (
    BouncedForwardedAssignMessage,
)
from arkitekt.messages.postman.provide.bounced_provide import BouncedProvideMessage
from arkitekt.messages.postman.unassign.bounced_forwarded_unassign import (
    BouncedForwardedUnassignMessage,
)
from arkitekt.messages.postman.unprovide.bounced_unprovide import (
    BouncedUnprovideMessage,
)
from arkitekt.messages.postman.assign.assign_cancelled import AssignCancelledMessage
from arkitekt.messages.postman.unassign.bounced_forwarded_unassign import (
    BouncedForwardedUnassignMessage,
)
from arkitekt.messages.postman.provide.provide_transition import (
    ProvideState,
    ProvideTransitionMessage,
)
from arkitekt.messages.postman.provide.provide_log import ProvideLogMessage
from arkitekt.messages.postman.log import LogLevel
from arkitekt.messages.postman.assign.assign_log import AssignLogMessage
from arkitekt.messages.postman.assign.assign_critical import AssignCriticalMessage
from arkitekt.messages.postman.assign.bounced_forwarded_assign import (
    BouncedForwardedAssignMessage,
)
from arkitekt.messages.postman.assign.bounced_assign import BouncedAssignMessage
from arkitekt.messages.postman.provide.provide_critical import ProvideCriticalMessage


import logging

logger = logging.getLogger(__name__)


class StandardAgent(Agent):
    @abstractmethod
    async def on_bounced_provide(message: BouncedProvideMessage):
        raise NotImplementedError()

    @abstractmethod
    async def on_bounced_unprovide(message: BouncedUnprovideMessage):
        raise NotImplementedError()

    @abstractmethod
    async def on_bounced_assign(message: BouncedForwardedAssignMessage):
        raise NotImplementedError()

    @abstractmethod
    async def on_bounced_unassign(message: BouncedForwardedUnassignMessage):
        raise NotImplementedError()

    async def handle_bounced_provide(self, message: BouncedProvideMessage):
        try:
            await self.on_bounced_provide(message)
            await self.transport.forward(
                ProvideLogMessage.from_log(
                    message.meta.reference,
                    "Forwarded to Agent",
                    extensions=message.meta.extensions,
                )
            )
        except Exception as e:
            logger.error(e)
            await self.transport.forward(
                ProvideTransitionMessage.from_critical(
                    message.meta.reference, e, extensions=message.meta.extensions
                )
            )

    async def handle_bounced_unprovide(self, message: BouncedUnprovideMessage):
        try:
            await self.on_bounced_unprovide(message)
            await self.transport.forward(
                ProvideLogMessage.from_log(
                    message.data.provision,
                    "Actor Delation Happening",
                    extensions=message.meta.extensions,
                )
            )
        except Exception as e:
            logger.error(e)
            await self.transport.forward(
                ProvideTransitionMessage.from_critical(
                    message.data.provision, e, extensions=message.meta.extensions
                )
            )

    async def handle_bounced_assign(self, message: BouncedForwardedAssignMessage):
        try:
            await self.on_bounced_assign(message)
            await self.transport.forward(
                AssignLogMessage.from_log(
                    message.meta.reference,
                    "Forwared Assignment",
                    extensions=message.meta.extensions,
                )
            )

        except Exception as e:
            await self.transport.forward(
                AssignCriticalMessage.from_critical(
                    message.meta.reference, e, extensions=message.meta.extensions
                )
            )
            raise e

    async def handle_bounced_unassign(self, message: BouncedForwardedUnassignMessage):
        try:
            await self.on_bounced_unassign(message)
            await self.transport.forward(
                AssignLogMessage.from_log(
                    message.data.assignation,
                    "Received Cancellation",
                    extensions=message.meta.extensions,
                )
            )

        except Exception as e:
            logger.error(e)
            await self.transport.forward(
                AssignCriticalMessage.from_critical(
                    message.data.assignation, e, extensions=message.meta.extensions
                )
            )
            raise e
