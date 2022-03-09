import pytest
from rath.links import compose, ShrinkingLink, DictingLink
from rath.links.testing.mock import AsyncMockLink
from arkitekt.agents.transport.protocols.agent_json import AssignationChangedMessage
from arkitekt.messages import T, Assignation, Provision
from tests.mocks import ArkitektMockResolver
from arkitekt.rath import ArkitektRath

from arkitekt.definition.registry import DefinitionRegistry, register
from arkitekt.structures.registry import StructureRegistry
from arkitekt.agents.stateful import StatefulAgent
from arkitekt.agents.transport.mock import MockAgentTransport
import asyncio
from arkitekt.actors.functional import FunctionalFuncActor
from arkitekt.actors.actify import actify


@pytest.fixture
def arkitekt_rath():

    link = compose(
        ShrinkingLink(),
        DictingLink(),  # after the shrinking so we can override the dicting
        AsyncMockLink(
            resolver=ArkitektMockResolver(),
        ),
    )

    return ArkitektRath(link)


@pytest.fixture
def mock_agent():

    transport = MockAgentTransport()

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
        return i

    base_agent = StatefulAgent(
        transport=transport,
        definition_registry=definition_registry,
    )

    return base_agent


async def test_actor_basic(mock_agent, arkitekt_rath):
    transport = mock_agent.transport

    async def call_me(i: int) -> str:
        return i + 1

    x = actify(call_me)(Provision(provision="1", template="1"), mock_agent)

    async with arkitekt_rath:
        async with mock_agent as agent:
            async with x:
                ##await x.on_assign(Assignation(assignation="1", provision="1", args=[1]))

                # x = await transport.receive(timeout=1)
                # assert isinstance(
                #    x, AssignationChangedMessage
                # ), "Should be an assignation changed message"
                pass
