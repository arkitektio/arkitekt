from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel
from arkitekt.api.schema import TemplateFragment, acreate_template, adefine, afind
from arkitekt.definition.registry import (
    DefinitionRegistry,
    get_current_definition_registry,
)
from arkitekt.arkitekt import Arkitekt, get_current_arkitekt
from koil import koil


class AgentTransport:
    def __init__(self) -> None:
        pass

    def __call__(self, agent) -> Any:
        self.agent = agent
        pass

    async def broadcast(self, message: str) -> None:
        await self.agent.broadcast(message)

    def aconnect(self):
        pass


ClientID = str
UserID = str


class Provision:
    def __init__(self):
        pass


class Actor:
    def __init__(self, template: TemplateFragment):
        self.template = template


class Agent:
    """Agent

    Agents are the governing entities in the arkitekt system. They are responsible for
    spawning and managing the lifecycle of Actors and registering Templates with the help
    of the DefinitionRegistry.

    """

    def __init__(
        self, defintion_registry: DefinitionRegistry = None, arkitekt: Arkitekt = None
    ) -> None:
        self.defintion_registry = (
            defintion_registry or get_current_definition_registry()
        )
        self.arkitekt = arkitekt or get_current_arkitekt()

        self.approvedTemplates: List[
            Tuple[TemplateFragment, Callable]
        ] = []  # Template is approved

        # IMportant Maps
        self.templateActorBuilderMap = {}
        self.templateTemplatesMap = {}

    async def aregister_definitions(self):
        if self.defintion_registry.templatedNodes:
            for (
                q_string,
                defined_actor,
                params,
            ) in self.defintion_registry.templatedNodes:
                version = params.get("version", "main")

                arkitekt_node = await afind(q=q_string)

                arkitekt_template = await acreate_template(
                    node=arkitekt_node,
                    params=params,
                    version=version,
                )

                self.approvedTemplates.append(
                    (arkitekt_template, defined_actor, params)
                )

        if self.defintion_registry.definedNodes:
            for (
                definition,
                defined_actor,
                params,
            ) in self.defintion_registry.definedNodes:
                # Defined Node are nodes that are not yet reflected on arkitekt (i.e they dont have an instance
                # id so we are trying to send them to arkitekt)
                arkitekt_node = await adefine(definition=definition)
                version = params.get("version", "main")

                arkitekt_template = await acreate_template(
                    node=arkitekt_node,
                    params=params,
                    version=version,
                )

                self.approvedTemplates.append(
                    (arkitekt_template, defined_actor, params)
                )

        if self.approvedTemplates:

            for arkitekt_template, defined_actor, params in self.approvedTemplates:
                # Generating Maps for Easy access
                self.templateActorBuilderMap[arkitekt_template.id] = defined_actor
                self.templateTemplatesMap[arkitekt_template.id] = arkitekt_template
