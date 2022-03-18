import pytest
from rath.links import compose, ShrinkingLink, DictingLink
from rath.links.testing.mock import AsyncMockLink
from arkitekt.actors.base import Agent
from arkitekt.agents.transport.protocols.agent_json import (
    AssignationChangedMessage,
    ProvisionChangedMessage,
)
from arkitekt.api.schema import AssignationStatus, ProvisionStatus
from arkitekt.messages import Assignation, Provision
from tests.funcs import function_with_side_register
from tests.mocks import ArkitektMockResolver, MockApp, MockArkitekt
from arkitekt.rath import ArkitektRath

from arkitekt.definition.registry import DefinitionRegistry, register
from arkitekt.structures.registry import StructureRegistry
from arkitekt.agents.stateful import StatefulAgent
from arkitekt.agents.transport.mock import MockAgentTransport
import asyncio

from tests.structures import SecondObject


@pytest.fixture
def complex_definition_registry():
    """Tests async expansion in a threaded context

    Args:
        arkitekt_client (_type_): _description_

    Returns:
        _type_: _description_
    """

    structure_registry = StructureRegistry()

    async def expand_second(id):
        return SecondObject(id)

    async def shrink_second(object):
        return object.id

    structure_registry.register_as_structure(
        SecondObject, "second", expand_second, shrink_second
    )

    definition_registry = DefinitionRegistry(structure_registry=structure_registry)

    definition_registry.register(function_with_side_register)

    return definition_registry


async def test_agent_assignation():

    mockapp = MockApp()

    @mockapp.arkitekt.register()
    async def hallo_world(i: int) -> int:
        """Hallo World

        Hallo world is a mini function

        Args:
            i (int): My little poney

        Returns:
            int: Anoter little int
        """
        return i + 1

    async with mockapp:
        mock_agent = mockapp.arkitekt.agent
        transport = mockapp.arkitekt.agent.transport

        await mock_agent.start()
        await transport.delay(Provision(provision="1", template="1"))
        await mock_agent.step()

        p = await transport.receive(timeout=1)
        print(p)
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
        await mock_agent.step()

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


async def test_complex_agent_gen(complex_definition_registry):

    mockapp = MockApp(
        arkitekt=MockArkitekt(
            definition_registry=complex_definition_registry,
        )
    )

    transport: MockAgentTransport = mockapp.arkitekt.agent.transport
    a: Agent = mockapp.arkitekt.agent

    async with mockapp:

        await a.astart()

        await transport.delay(Provision(provision="1", template="1"))
        await a.astep()

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

        await a.astep()

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
