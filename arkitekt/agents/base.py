from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union
from arkitekt.api.schema import TemplateFragment, acreate_template, adefine, afind
from arkitekt.definition.registry import (
    DefinitionRegistry,
    get_current_definition_registry,
)
from arkitekt.arkitekt import Arkitekt, get_current_arkitekt
import asyncio
from arkitekt.agents.transport.base import AgentTransport
from arkitekt.messages import Assignation, Unassignation, Unprovision, Provision


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
        arkitekt: Arkitekt = None,
    ) -> None:
        self.transport = transport
        self.transport.broadcast = self.broadcast

        self.definition_registry = (
            definition_registry or get_current_definition_registry()
        )
        self.arkitekt = arkitekt or get_current_arkitekt()

        self.approvedTemplates: List[
            Tuple[TemplateFragment, Callable]
        ] = []  # Template is approved

        # IMportant Maps
        self.templateActorBuilderMap = {}
        self.templateTemplatesMap = {}
        self.provisionActorMap = {}
        self.provisionTaskMap = {}

    async def broadcast(
        self, message: Union[Assignation, Provision, Unassignation, Unprovision]
    ):
        pass

    async def aconnect(self):
        await self.aregister_definitions()
        await self.transport.aconnect()

    async def aregister_definitions(self):
        if self.definition_registry.templatedNodes:
            for (
                q_string,
                actor_builder,
                params,
            ) in self.definition_registry.templatedNodes:
                version = params.get("version", "main")

                arkitekt_node = await afind(q=q_string)

                arkitekt_template = await acreate_template(
                    node=arkitekt_node.id,
                    params=params,
                    version=version,
                    arkitekt=self.arkitekt,
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
                arkitekt_node = await adefine(
                    definition=definition, arkitekt=self.arkitekt
                )
                version = params.get("version", "main")
                arkitekt_template = await acreate_template(
                    node=arkitekt_node.id,
                    params={},  # Todo really make this happen
                    version=version,
                    arkitekt=self.arkitekt,
                )

                self.approvedTemplates.append(
                    (arkitekt_template, actor_builder, params)
                )

        if self.approvedTemplates:

            for arkitekt_template, defined_actor, params in self.approvedTemplates:
                # Generating Maps for Easy access
                self.templateActorBuilderMap[arkitekt_template.id] = defined_actor
                self.templateTemplatesMap[arkitekt_template.id] = arkitekt_template

    async def adisconnect(self):
        await self.transport.adisconnect()

    async def __aenter__(self):
        print("Self disconnecting")
        await self.aconnect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print("Agent Disconneting")
        await self.adisconnect()
