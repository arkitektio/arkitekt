from typing import Callable, Dict, List, Optional, Tuple, Union

from pydantic import Field
from arkitekt.api.schema import TemplateFragment, acreate_template, adefine, afind
from arkitekt.definition.registry import (
    DefinitionRegistry,
    get_current_definition_registry,
)
from arkitekt.rath import ArkitektRath, current_arkitekt_rath
import asyncio
from arkitekt.agents.transport.base import AgentTransport
from arkitekt.messages import Assignation, Unassignation, Unprovision, Provision
from koil import unkoil
from koil.composition import KoiledModel


class BaseAgent(KoiledModel):
    """Agent

    Agents are the governing entities in the arkitekt system. They are responsible for
    spawning and managing the lifecycle of Actors and registering Templates with the help
    of the DefinitionRegistry.

    """

    transport: Optional[AgentTransport] = None
    definition_registry: Optional[DefinitionRegistry] = None
    rath: Optional[ArkitektRath] = None

    _approved_templates: List[Tuple[TemplateFragment, Callable]] = []
    _templateActorBuilderMap = {}
    _templateTemplatesMap: Dict[str, TemplateFragment] = {}
    _provisionActorMap = {}
    _provisionTaskMap: Dict[str, asyncio.Task] = Field(default_factory=dict)
    _inqueue: Optional[asyncio.Queue] = None

    async def abroadcast(
        self, message: Union[Assignation, Provision, Unassignation, Unprovision]
    ):
        await self._inqueue.put(message)

    async def process(self):
        raise NotImplementedError(
            "This method needs to be implemented by the agents subclass"
        )

    async def aregister_definitions(self):
        if self.definition_registry.templated_nodes:
            for (
                q_string,
                actor_builder,
                params,
            ) in self.definition_registry.templated_nodes:
                version = params.get("version", "main")

                arkitekt_node = await afind(q=q_string, rath=self.rath)

                arkitekt_template = await acreate_template(
                    node=arkitekt_node.id,
                    params=params,
                    version=version,
                    rath=self.rath,
                )

                self._approved_templates.append(
                    (arkitekt_template, actor_builder, params)
                )

        if self.definition_registry.defined_nodes:
            for (
                definition,
                actor_builder,
                params,
            ) in self.definition_registry.defined_nodes:
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

                self._approved_templates.append(
                    (arkitekt_template, actor_builder, params)
                )

        if self._approved_templates:

            for arkitekt_template, defined_actor, params in self._approved_templates:
                # Generating Maps for Easy access
                self._templateActorBuilderMap[arkitekt_template.id] = defined_actor
                self._templateTemplatesMap[arkitekt_template.id] = arkitekt_template

    async def astep(self):
        await self.process(await self._inqueue.get())

    async def astart(self):
        await self.aregister_definitions()

        data = await self.transport.list_provisions()

        for prov in data:
            await self.abroadcast(prov)

        data = await self.transport.list_assignations()

        for ass in data:
            await self.abroadcast(ass)

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

    async def __aenter__(self):
        self.definition_registry = (
            self.definition_registry or get_current_definition_registry()
        )
        self.rath = self.rath or current_arkitekt_rath.get()
        self._inqueue = asyncio.Queue()
        self.transport.abroadcast = self.abroadcast
        await self.transport.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.transport.__aexit__(exc_type, exc_val, exc_tb)

    class Config:
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True
