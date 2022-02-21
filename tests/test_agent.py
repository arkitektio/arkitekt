import pytest
from rath.links import compose, ShrinkingLink, DictingLink
from rath.links.testing.mock import AsyncMockLink
from tests.mocks import ArkitektQueryResolver, ArkitektMutationResolver, MockTransport
from arkitekt import Arkitekt

from arkitekt.definition.registry import DefinitionRegistry, register
from arkitekt.structures.registry import StructureRegistry
from arkitekt.agents.stateful import StatefulAgent


@pytest.fixture
def arkitekt_client():

    link = compose(
        ShrinkingLink(),
        DictingLink(),  # after the shrinking so we can override the dicting
        AsyncMockLink(
            query_resolver=ArkitektQueryResolver(),
            mutation_resolver=ArkitektMutationResolver(),
        ),
    )

    return Arkitekt(link)


async def test_agent_registration(arkitekt_client):
    transport = MockTransport()

    structure_registry = StructureRegistry()
    definition_registry = DefinitionRegistry()

    @register(
        definition_registry=definition_registry, structure_registry=structure_registry
    )
    def hallo_world(i: int) -> str:
        """Hallo World

        Hallo world is a mini function

        Args:
            i (int): My little poney

        Returns:
            str: A nother little poney in string
        """

    base_agent = StatefulAgent(
        transport=transport,
        definition_registry=definition_registry,
        arkitekt=arkitekt_client,
    )

    await base_agent.aregister_definitions()
