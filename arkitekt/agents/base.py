from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union
from arkitekt.api.schema import TemplateFragment, acreate_template, adefine, afind
from arkitekt.definition.registry import (
    DefinitionRegistry,
    get_current_definition_registry,
)
from arkitekt.rath import ArkitektRath, current_arkitekt_rath
import asyncio
from arkitekt.agents.transport.base import AgentTransport
from arkitekt.messages import Assignation, Unassignation, Unprovision, Provision
from koil import unkoil, unkoil_gen


class BaseAgent:
    """Agent

    Agents are the governing entities in the arkitekt system. They are responsible for
    spawning and managing the lifecycle of Actors and registering Templates with the help
    of the DefinitionRegistry.

    """

    def __init__(
        self,
        transport: AgentTransport,
        definition_registry: DefinitionRegistry = None,
        rath: ArkitektRath = None,
    ) -> None:
        self.transport = transport
        self.definition_registry = (
            definition_registry or get_current_definition_registry()
        )

        self.approvedTemplates: List[
            Tuple[TemplateFragment, Callable]
        ] = []  # Template is approved
        self.rath = rath
        # IMportant Maps
        self.templateActorBuilderMap = {}
        self.templateTemplatesMap = {}
        self.provisionActorMap = {}
        self.provisionTaskMap = {}

    async def broadcast(
        self, message: Union[Assignation, Provision, Unassignation, Unprovision]
    ):
        await self._inqueue.put(message)

    async def aconnect(self):
        await self.transport.aconnect()

    async def process(self):
        raise NotImplementedError(
            "This method needs to be implemented by the agents subclass"
        )

    async def aregister_definitions(self):
        if self.definition_registry.templatedNodes:
            for (
                q_string,
                actor_builder,
                params,
            ) in self.definition_registry.templatedNodes:
                version = params.get("version", "main")

                arkitekt_node = await afind(q=q_string, rath=self.rath)

                arkitekt_template = await acreate_template(
                    node=arkitekt_node.id,
                    params=params,
                    version=version,
                    rath=self.rath,
                )

                self.approvedTemplates.append(
                    (arkitekt_template, actor_builder, params)
                )

        if self.definition_registry.definedNodes:
            for (
                definition,
                actor_builder,
                params,
            ) in self.definition_registry.definedNodes:
                # Defined Node are nodes that are not yet reflected on arkitekt (i.e they dont have an instance
                # id so we are trying to send them to arkitekt)
                arkitekt_node = await adefine(definition=definition, rath=self.rath)
                version = params.get("version", "main")
                arkitekt_template = await acreate_template(
                    node=arkitekt_node.id,
                    params={},  # Todo really make this happen
                    version=version,
                    rath=self.rath,
                )

                self.approvedTemplates.append(
                    (arkitekt_template, actor_builder, params)
                )

        if self.approvedTemplates:

            for arkitekt_template, defined_actor, params in self.approvedTemplates:
                # Generating Maps for Easy access
                self.templateActorBuilderMap[arkitekt_template.id] = defined_actor
                self.templateTemplatesMap[arkitekt_template.id] = arkitekt_template

    async def astep(self):
        await self.process(await self._inqueue.get())

    async def astart(self):
        await self.aregister_definitions()

        data = await self.transport.list_provisions()

        for prov in data:
            await self.broadcast(prov)

        data = await self.transport.list_assignations()

        for ass in data:
            await self.broadcast(ass)

    def step(self, *args, **kwargs):
        return unkoil(self.astep, *args, **kwargs)

    def start(self, *args, **kwargs):
        return unkoil(self.astart, *args, **kwargs)

    def provide(self, *args, **kwargs):
        return unkoil(self.aprovide, *args, **kwargs)

    async def aprovide(self):
        await self.astart()
        while True:
            await self.astep()

    async def adisconnect(self):
        await self.transport.adisconnect()

    async def __aenter__(self):
        self.rath = self.rath or current_arkitekt_rath.get()
        self._inqueue = asyncio.Queue()
        self.transport.broadcast = self.broadcast
        await self.aconnect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.adisconnect()
