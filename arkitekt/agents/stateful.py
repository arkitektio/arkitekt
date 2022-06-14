from arkitekt.agents.base import BaseAgent
from arkitekt.agents.errors import AgentException, ProvisionException
from arkitekt.api.schema import AssignationStatus, ProvisionStatus
from arkitekt.messages import Assignation, Provision, Unassignation, Unprovision
from typing import Union
import asyncio
import logging

logger = logging.getLogger(__name__)


class StatefulAgent(BaseAgent):
    """An agent that tries to recover and
    take care of all the assignations and provisions

    Args:
        BaseAgent (_type_): _description_
    """

    async def process(
        self, message: Union[Assignation, Provision, Unassignation, Unprovision]
    ):
        logger.info(f"Agent received {message}")

        if isinstance(message, Assignation) or isinstance(message, Unassignation):
            if message.provision in self.provisionActorMap:
                actor = self.provisionActorMap[message.provision]
                await actor.apass(message)
            else:
                logger.warning(
                    f"Received assignation for a provision that is not running {self.provisionActorMap} {message.provision}"
                )
                await self.transport.change_assignation(
                    message.assignation,
                    status=AssignationStatus.CRITICAL,
                    message="Actor that handles this provision is not available",
                )

        elif isinstance(message, Provision):
            try:
                await self.aspawn_actor(message)
            except ProvisionException as e:
                logger.error("Spawning error", exc_info=True)
                await self.transport.change_provision(
                    message.provision, status=ProvisionStatus.DENIED, message=str(e)
                )

        elif isinstance(message, Unprovision):
            if message.provision in self.provisionActorMap:
                actor = self.provisionActorMap[message.provision]
                await actor.astop()
                del self.provisionActorMap[message.provision]
                logger.info("Actor stopped")

            else:
                logger.error(
                    f"Received Unprovision for never provisioned provision {message}"
                )

        else:
            raise AgentException(f"Unknown message type {type(message)}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):

        cancelations = [actor.astop() for actor in self.provisionActorMap.values()]

        for c in cancelations:
            try:
                await c
            except asyncio.CancelledError:
                pass

        await super().__aexit__(exc_type, exc_val, exc_tb)
