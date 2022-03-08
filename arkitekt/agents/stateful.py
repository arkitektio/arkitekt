from arkitekt.agents.base import BaseAgent
from arkitekt.api.schema import AssignationStatus, ProvisionStatus
from arkitekt.messages import Assignation, Provision, Unassignation, Unprovision
from typing import Optional, Union
import asyncio
import logging

logger = logging.getLogger(__name__)


class StatefulAgent(BaseAgent):
    """An agent that tries to recover and
    take care of all the assignations and provisions

    Args:
        BaseAgent (_type_): _description_
    """

    async def aconnect(self):
        await super().aconnect()

    async def aprovide(self):
        data = await self.transport.list_provisions()

        for prov in data:
            await self.broadcast(prov)

        data = await self.transport.list_assignations()

        for ass in data:
            await self.broadcast(ass)

        while True:
            await asyncio.sleep(0.1)

    async def broadcast(
        self, message: Union[Assignation, Provision, Unassignation, Unprovision]
    ):
        logger.info(f"Agent received {message}")

        if isinstance(message, Assignation) or isinstance(message, Unassignation):
            if message.provision in self.provisionActorMap:
                actor = self.provisionActorMap[message.provision]
                await actor.apass(message)
            else:
                await self.transport.change_assignation(
                    message.assignation,
                    status=AssignationStatus.CRITICAL,
                    message="Actor that handles this provision is not available",
                )

        elif isinstance(message, Provision):
            if message.template in self.templateActorBuilderMap:
                actorBuilder = self.templateActorBuilderMap[message.template]
                self.provisionActorMap[message.provision] = actorBuilder(message, self)
                await self.provisionActorMap[message.provision].arun()
                logger.info("Actor started")
            else:
                logger.info("Actor not found")
                await self.transport.change_provision(
                    message.provision,
                    status=ProvisionStatus.DENIED,
                    message="No actor found on the provisioning Agent, this is most likely due to a change in this agent's configuration",
                )

        elif isinstance(message, Unprovision):
            await self.provisionActorMap[message.provision].astop()

        else:
            raise Exception(f"Unknown message type {type(message)}")

    async def adisconnect(self):
        await super().adisconnect()
        cancelations = [actor.astop() for actor in self.provisionActorMap.values()]

        for c in cancelations:
            try:
                await c
            except asyncio.CancelledError:
                print(f"Cancelled Actor {c}")
