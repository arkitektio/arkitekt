from arkitekt.agents.base import BaseAgent
from arkitekt.agents.messages import Assignation, Provision
import asyncio


class StatefulAgent(BaseAgent):
    """An agent that tries to recover and
    take care of all the assignations and provisions

    Args:
        BaseAgent (_type_): _description_
    """

    async def aconnect(self):
        await self.transport.aconnect()

    async def astart(self):
        data = await self.transport.list_provisions()

        for prov in data:
            actorBuilder = self.templateActorBuilderMap[prov.template]
            self.provisionActorMap[prov.provision] = actorBuilder()
            task = asyncio.create_task(
                self.provisionActorMap[prov.provision].arun(prov, self)
            )
            task.add_done_callback(print)

        data = await self.transport.list_assignations()
        for ass in data:
            actor = self.provisionActorMap[ass.provision]
            task = asyncio.create_task(actor.apass(ass))
            task.add_done_callback(print)

    async def _on_new_assign(self, res: Assignation):
        raise NotImplementedError()

    async def _on_new_provide(self, ass: Provision):
        raise NotImplementedError()
