from arkitekt.agents.base import BaseAgent
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
            if message.provision in self._provisionActorMap:
                actor = self._provisionActorMap[message.provision]
                await actor.apass(message)
            else:
                await self.transport.change_assignation(
                    message.assignation,
                    status=AssignationStatus.CRITICAL,
                    message="Actor that handles this provision is not available",
                )

        elif isinstance(message, Provision):
            if message.template in self._templateActorBuilderMap:
                actorBuilder = self._templateActorBuilderMap[message.template]
                self._provisionActorMap[message.provision] = actorBuilder(message, self)
                await self._provisionActorMap[message.provision].arun()
                logger.info("Actor started")
            else:
                logger.info("Actor not found")
                await self.transport.change_provision(
                    message.provision,
                    status=ProvisionStatus.DENIED,
                    message="No actor found on the provisioning Agent, this is most likely due to a change in this agent's configuration",
                )

        elif isinstance(message, Unprovision):
            await self._provisionActorMap[message.provision].astop()

        else:
            raise Exception(f"Unknown message type {type(message)}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):

        cancelations = [actor.astop() for actor in self._provisionActorMap.values()]

        for c in cancelations:
            try:
                await c
            except asyncio.CancelledError:
                print(f"Cancelled Actor {c}")

        await super().__aexit__(exc_type, exc_val, exc_tb)
