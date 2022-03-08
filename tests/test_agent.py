import pytest
from rath.links import compose, ShrinkingLink, DictingLink
from rath.links.testing.mock import AsyncMockLink
from arkitekt.agents.transport.protocols.agent_json import (
    AssignationChangedMessage,
    ProvisionChangedMessage,
)
from arkitekt.api.schema import AssignationStatus, ProvisionStatus
from arkitekt.messages import Assignation, Provision
from tests.funcs import function_with_side_register
from tests.mocks import ArkitektMockResolver
from arkitekt.rath import ArkitektRath

from arkitekt.definition.registry import DefinitionRegistry, register
from arkitekt.structures.registry import StructureRegistry
from arkitekt.agents.stateful import StatefulAgent
from arkitekt.agents.transport.mock import MockAgentTransport
import asyncio

from tests.structures import SecondObject


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
def agent_complex_object():
    """Tests async expansion in a threaded context

    Args:
        arkitekt_client (_type_): _description_

    Returns:
        _type_: _description_
    """
    transport = MockAgentTransport()

    structure_registry = StructureRegistry()
    definition_registry = DefinitionRegistry()

    async def expand_second(id):
        return SecondObject(id)

    async def shrink_second(object):
        return object.id

    structure_registry.register_as_structure(
        SecondObject, "second", expand_second, shrink_second
    )

    register(
        definition_registry=definition_registry, structure_registry=structure_registry
    )(function_with_side_register)

    return StatefulAgent(
        transport=transport,
        definition_registry=definition_registry,
    )


@pytest.fixture
def mock_agent():

    transport = MockAgentTransport()

    structure_registry = StructureRegistry()
    definition_registry = DefinitionRegistry()

    @register(
        definition_registry=definition_registry, structure_registry=structure_registry
    )
    async def hallo_world(i: int) -> int:
        """Hallo World

        Hallo world is a mini function

        Args:
            i (int): My little poney

        Returns:
            int: Anoter little int
        """
        return i + 1

    base_agent = StatefulAgent(
        transport=transport,
        definition_registry=definition_registry,
    )

    return base_agent


async def test_agent_assignation(mock_agent, arkitekt_rath):

    transport: MockAgentTransport = mock_agent.transport

    async with arkitekt_rath:
        async with mock_agent:
            await transport.delay(Provision(provision="1", template="1"))

            p = await transport.receive(timeout=1)
            assert isinstance(p, ProvisionChangedMessage)
            assert (
                p.status == ProvisionStatus.PROVIDING
            ), f"First provision should be providing {p.message}"

            p = await transport.receive(timeout=1)
            assert isinstance(p, ProvisionChangedMessage)
            assert (
                p.status == ProvisionStatus.ACTIVE
            ), f"The provision should be active {p.message}"

            await transport.delay(Assignation(provision="1", assignation="1", args=[1]))

            a = await transport.receive(timeout=1)
            assert isinstance(a, AssignationChangedMessage)
            assert (
                a.status == AssignationStatus.ASSIGNED
            ), f"The assignaiton should be assigned {a.message}"

            a = await transport.receive(timeout=1)
            assert isinstance(a, AssignationChangedMessage)
            assert (
                a.status == AssignationStatus.RETURNED
            ), f"The assignaiton should have returned {a.message}"
            assert a.returns == [2], f"The provision should have returned {a.message}"


async def test_complex_agent_gen(agent_complex_object, arkitekt_rath):

    transport: MockAgentTransport = agent_complex_object.transport
    async with arkitekt_rath:
        async with agent_complex_object:
            await transport.delay(Provision(provision="1", template="1"))

            p = await transport.receive(timeout=1)
            assert isinstance(p, ProvisionChangedMessage)
            assert (
                p.status == ProvisionStatus.PROVIDING
            ), f"First provision should be providing {p.message}"

            p = await transport.receive(timeout=1)
            assert isinstance(p, ProvisionChangedMessage)
            assert (
                p.status == ProvisionStatus.ACTIVE
            ), f"The provision should be active {p.message}"

            await transport.delay(
                Assignation(
                    provision="1",
                    assignation="1",
                    args=[[1]],
                    kwargs={"name": {"hallo": 1}},
                )
            )

            a = await transport.receive(timeout=1)
            assert isinstance(a, AssignationChangedMessage)
            assert (
                a.status == AssignationStatus.ASSIGNED
            ), f"The assignaiton should be assigned {a.message}"

            a = await transport.receive(timeout=1)
            assert isinstance(a, AssignationChangedMessage)
            assert (
                a.status == AssignationStatus.YIELD
            ), f"The assignaiton should have returned {a.message}"
            assert a.returns == [
                "tested",
                {"peter": 6},
            ], f"The provision should have returned {a.message}"

            a = await transport.receive(timeout=1)
            assert isinstance(a, AssignationChangedMessage)
            assert (
                a.status == AssignationStatus.DONE
            ), f"The assignaiton should have been done {a.message}"
