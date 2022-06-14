from typing import Any, Awaitable, Callable, Dict, List
from pydantic import Field
from arkitekt.agents.stateful import StatefulAgent
from arkitekt.api.schema import TemplateFragment, WidgetInput
from arkitekt.postmans.stateful import StatefulPostman
from arkitekt.rath import ArkitektRath
from arkitekt.messages import Provision
from arkitekt.structures.default import get_default_structure_registry
from arkitekt.structures.registry import (
    StructureRegistry,
)

from arkitekt.definition.registry import (
    DefinitionRegistry,
    get_current_definition_registry,
)
from arkitekt.agents.base import BaseAgent
from arkitekt.postmans.base import BasePostman
from koil import unkoil
from koil.composition import Composition
from koil.decorators import koilable


@koilable(fieldname="koil", add_connectors=True)
class Arkitekt(Composition):
    rath: ArkitektRath = Field(default_factory=ArkitektRath)
    structure_registry: StructureRegistry = Field(
        default_factory=get_default_structure_registry
    )
    definition_registry: DefinitionRegistry = Field(
        default_factory=get_current_definition_registry
    )
    agent: BaseAgent = Field(default_factory=StatefulAgent)
    postman: BasePostman = Field(default_factory=StatefulPostman)

    def register(
        self,
        builder=None,
        widgets: Dict[str, WidgetInput] = {},
        interfaces: List[str] = [],
        on_provide: Callable[[Provision, TemplateFragment], Awaitable[Any]] = None,
        on_unprovide: Callable[[], Awaitable[Any]] = None,
        structure_registry: StructureRegistry = None,
        **actorparams,
    ) -> None:
        """
        Register a new function
        """
        structure_registry = structure_registry or self.structure_registry

        def real_decorator(function):
            # Simple bypass for now
            def wrapped_function(*args, **kwargs):
                return function(*args, **kwargs)

            self.definition_registry.register(
                function,
                builder=builder,
                widgets=widgets,
                interfaces=interfaces,
                structure_registry=structure_registry,
                on_provide=on_provide,
                on_unprovide=on_unprovide,
                **actorparams,
            )

        return real_decorator

    def run(self, *args, **kwargs) -> None:
        """
        Run the application.
        """
        return unkoil(self.arun, *args, **kwargs)

    async def arun(self) -> None:
        """
        Run the application.
        """
        assert self.agent.transport.connected, "Transport is not connected"
        await self.agent.aprovide()

    class Config:
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True
        extra = "forbid"
