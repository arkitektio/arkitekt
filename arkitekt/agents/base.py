from typing import Callable, Dict, List, Optional, Tuple, Union

from pydantic import Field
import inspect
from arkitekt.actors.base import Actor
from arkitekt.actors.transport import ActorTransport, SharedTransport
from arkitekt.actors.types import ActorBuilder
from arkitekt.agents.transport.fakts import FaktsWebsocketAgentTransport
from arkitekt.agents.transport.mock import MockAgentTransport
from arkitekt.agents.transport.websocket import WebsocketAgentTransport
from arkitekt.api.schema import (
    ProvisionFragment,
    TemplateFragment,
    acreate_template,
    adefine,
    afind,
    aget_provision,
)
from arkitekt.definition.registry import (
    DefinitionRegistry,
    get_current_definition_registry,
)
from arkitekt.rath import ArkitektRath, current_arkitekt_rath
import asyncio
from arkitekt.agents.transport.base import AgentTransport, Contextual
from arkitekt.messages import Assignation, Unassignation, Unprovision, Provision
from koil import unkoil
from koil.composition import KoiledModel
import logging


logger = logging.getLogger(__name__)


class BaseAgent(KoiledModel):
    """Agent

    Agents are the governing entities in the arkitekt system. They are responsible for
    spawning and managing the lifecycle of Actors and registering Templates with the help
    of the DefinitionRegistry.

    """

    transport: Optional[AgentTransport] = Field(
        default_factory=FaktsWebsocketAgentTransport
    )
    definition_registry: Optional[DefinitionRegistry] = None

    provisionProvisionMap: Dict[str, ProvisionFragment] = Field(default_factory=dict)
    provisionActorMap: Dict[str, Actor] = Field(default_factory=dict)

    rath: Optional[ArkitektRath] = None

    _hooks = {}

    _approved_templates: List[Tuple[TemplateFragment, Callable]] = []
    _templateActorBuilderMap: Dict[str, ActorBuilder] = {}
    _templateTemplatesMap: Dict[str, TemplateFragment] = {}
    _provisionTaskMap: Dict[str, asyncio.Task] = Field(default_factory=dict)
    _inqueue: Contextual[asyncio.Queue] = None

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

    def hook(self, on: str):
        def decorator(func):
            assert inspect.iscoroutinefunction(func), "needs to be a coroutine"
            self._hooks.setdefault(on, []).append(func)
            return func

        return decorator

    async def run_hook(self, hook_name: str, *args, **kwargs):
        for hook in self._hooks.get(hook_name, []):
            await hook(self, *args, **kwargs)

    async def aspawn_actor(self, message: Provision) -> Actor:
        """Spawns an Actor from a Provision"""

        await self.run_hook("before_spawn", message)
        prov = await aget_provision(message.provision)

        actor_builder = self._templateActorBuilderMap[prov.template.id]
        actor = actor_builder(
            provision=prov,
            transport=self.transport
        )
        await actor.arun()
        await self.run_hook("after_spawn", actor)
        self.provisionActorMap[prov.id] = actor
        self.provisionProvisionMap[prov.id] = prov
        return actor

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
        logger.info(
            f"Launching provisioning task. We are running {self.transport.instance_id}"
        )
        await self.astart()
        while True:
            await self.astep()

    async def __aenter__(self):
        self.definition_registry = (
            self.definition_registry or get_current_definition_registry()
        )
        self.rath = self.rath or current_arkitekt_rath.get()
        self._inqueue = asyncio.Queue()
        self.transport._abroadcast = self.abroadcast
        await self.transport.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.transport.__aexit__(exc_type, exc_val, exc_tb)

    class Config:
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True
