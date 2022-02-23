from arkitekt.agents.base import BaseAgent
from arkitekt.messages import Assignation, Provision, Unassignation, Unprovision
from typing import Optional, Union
import asyncio


class StatefulAgent(BaseAgent):
    """An agent that tries to recover and
    take care of all the assignations and provisions

    Args:
        BaseAgent (_type_): _description_
    """

    async def aconnect(self):
        await super().aconnect()
        await self.astart()

    async def astart(self):
        data = await self.transport.list_provisions()

        for prov in data:
            await self.broadcast(prov)

        data = await self.transport.list_assignations()
        for ass in data:
            await self.broadcast(ass)

    async def broadcast(
        self, message: Union[Assignation, Provision, Unassignation, Unprovision]
    ):

        if isinstance(message, Assignation) or isinstance(message, Unassignation):
            actor = self.provisionActorMap[message.provision]
            await actor.apass(message)

        if isinstance(message, Provision):
            actorBuilder = self.templateActorBuilderMap[message.template]
            self.provisionActorMap[message.provision] = actorBuilder(message, self)
            await self.provisionActorMap[message.provision].arun()

        if isinstance(message, Unprovision):
            await self.provisionActorMap[message.provision].astop()

        return await super().broadcast(message)

    async def adisconnect(self):
        await super().adisconnect()
        cancelations = [actor.astop() for actor in self.provisionActorMap.values()]

        for c in cancelations:
            try:
                await c
            except asyncio.CancelledError:
                print(f"Cancelled Actor {c}")
