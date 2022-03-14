import asyncio
import contextvars
from dataclasses import dataclass
from typing import Any, AsyncContextManager, Awaitable, Callable, Dict, List, Optional
from pydantic import BaseModel, Field, PrivateAttr
from arkitekt.api.schema import TemplateFragment, WidgetInput
from arkitekt.fakts.agent import FaktsAgent
from arkitekt.fakts.postman import FaktsPostman
from arkitekt.fakts.rath import FaktsArkitektRath
from arkitekt.rath import ArkitektRath
from arkitekt.messages import Provision
from arkitekt.structures.registry import (
    StructureRegistry,
    get_current_structure_registry,
)
from arkitekt.definition.registry import (
    DefinitionRegistry,
    get_current_definition_registry,
)
from arkitekt.agents.base import BaseAgent
from arkitekt.postmans.base import BasePostman
from fakts.fakts import Fakts
from herre.fakts.herre import FaktsHerre
from herre.herre import Herre
from koil import Koil, unkoil
import koil
from koil.decorators import koilable


@koilable(fieldname="koil", add_connectors=True)
class Arkitekt(BaseModel):
    rath: ArkitektRath = Field(default_factory=FaktsArkitektRath)
    structure_registry: StructureRegistry = Field(
        default_factory=get_current_structure_registry
    )
    definition_registry: DefinitionRegistry = Field(
        default_factory=get_current_definition_registry
    )
    agent: BaseAgent = Field(default_factory=FaktsAgent)
    postman: BasePostman = Field(default_factory=FaktsPostman)
    additional_contexts: List[AsyncContextManager] = []
    koil: Optional[Koil] = None

    _connected = False

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
        unkoil(self.arun, *args, **kwargs)

    async def arun(self) -> None:
        """
        Run the application.
        """
        assert (
            self._connected
        ), "You must be connected before you run. Please use `with` or `async with`."
        await self.agent.aprovide()

    async def __aenter__(self):
        self._connected = True

        await self.rath.__aenter__()

        await self.agent.__aenter__()
        await self.postman.__aenter__()

        for context in self.additional_contexts:
            await context.__aenter__()  # ATTENTION: GATHER DOES NOT COPY THE CONTEXT VARIABLES

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):

        for context in self.additional_contexts:
            await context.__aexit__(exc_type, exc_val, exc_tb)

        await self.agent.__aexit__(exc_type, exc_val, exc_tb)
        await self.postman.__aexit__(exc_type, exc_val, exc_tb)
        await self.rath.__aexit__(exc_type, exc_val, exc_tb)

    class Config:
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True
