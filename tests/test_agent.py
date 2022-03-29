import pytest
from arkitekt.actors.base import Agent
from arkitekt.agents.transport.protocols.agent_json import (
    AssignationChangedMessage,
    ProvisionChangedMessage,
)
from arkitekt.api.schema import AssignationStatus, ProvisionStatus
from arkitekt.messages import Assignation, Provision, Unassignation, Unprovision
from .funcs import function_with_side_register, function_with_side_register_async
from .mocks import MockApp, MockArkitekt

from arkitekt.definition.registry import DefinitionRegistry
from arkitekt.structures.registry import StructureRegistry
from arkitekt.agents.transport.mock import MockAgentTransport

from .structures import SecondObject


@pytest.fixture
def complex_structure_registry():
    structure_registry = StructureRegistry()

    async def expand_second(id):
        return SecondObject(id)

    async def shrink_second(object):
        return object.id

    structure_registry.register_as_structure(
        SecondObject, "second", expand_second, shrink_second
    )
    return structure_registry


@pytest.fixture
def complex_definition_registry(complex_structure_registry):
    definition_registry = DefinitionRegistry(
        structure_registry=complex_structure_registry
    )

    definition_registry.register(function_with_side_register)

    return definition_registry


@pytest.fixture
def complex_definition_registry_async(complex_structure_registry):
    definition_registry = DefinitionRegistry(
        structure_registry=complex_structure_registry
    )

    definition_registry.register(function_with_side_register_async)

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

        await mock_agent.astart()
        await transport.adelay(Provision(provision="1", template="1"))
        await mock_agent.astep()

        p = await transport.areceive(timeout=1)
        print(p)
        assert isinstance(p, ProvisionChangedMessage)
        assert (
            p.status == ProvisionStatus.PROVIDING
        ), f"First provision should be providing {p.message}"

        p = await transport.areceive(timeout=1)
        assert isinstance(p, ProvisionChangedMessage)
        assert (
            p.status == ProvisionStatus.ACTIVE
        ), f"The provision should be active {p.message}"

        await transport.adelay(Assignation(provision="1", assignation="1", args=[1]))
        await mock_agent.astep()

        a = await transport.areceive(timeout=1)
        assert isinstance(a, AssignationChangedMessage)
        assert (
            a.status == AssignationStatus.ASSIGNED
        ), f"The assignaiton should be assigned {a.message}"

        a = await transport.areceive(timeout=1)
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

        await transport.adelay(Provision(provision="1", template="1"))
        await a.astep()

        p = await transport.areceive(timeout=1)
        assert isinstance(p, ProvisionChangedMessage)
        assert (
            p.status == ProvisionStatus.PROVIDING
        ), f"First provision should be providing {p.message}"

        p = await transport.areceive(timeout=1)
        assert isinstance(p, ProvisionChangedMessage)
        assert (
            p.status == ProvisionStatus.ACTIVE
        ), f"The provision should be active {p.message}"

        await transport.adelay(
            Assignation(
                provision="1",
                assignation="1",
                args=[[1]],
                kwargs={"name": {"hallo": 1}},
            )
        )

        await a.astep()

        a = await transport.areceive(timeout=0.2)

        assert isinstance(a, AssignationChangedMessage)
        assert (
            a.status == AssignationStatus.ASSIGNED
        ), f"The assignaiton should be assigned {a.message}"

        a = await transport.areceive(timeout=0.3)
        assert isinstance(a, AssignationChangedMessage)
        assert (
            a.status == AssignationStatus.YIELD
        ), f"The assignaiton should have returned {a.message}"
        assert a.returns == [
            "tested",
            {"peter": 6},
        ], f"The provision should have returned {a.message}"

        a = await transport.areceive(timeout=1)
        assert isinstance(a, AssignationChangedMessage)
        assert (
            a.status == AssignationStatus.DONE
        ), f"The assignaiton should have been done {a.message}"


async def test_complex_agent_gen_assignation_cancellation(
    complex_definition_registry_async,
):

    mockapp = MockApp(
        arkitekt=MockArkitekt(
            definition_registry=complex_definition_registry_async,
        )
    )

    transport: MockAgentTransport = mockapp.arkitekt.agent.transport
    agent: Agent = mockapp.arkitekt.agent

    async with mockapp:

        await agent.astart()

        await transport.adelay(Provision(provision="1", template="1"))
        await agent.astep()

        p = await transport.areceive(timeout=1)
        assert isinstance(p, ProvisionChangedMessage)
        assert (
            p.status == ProvisionStatus.PROVIDING
        ), f"First provision should be providing {p.message}"

        p = await transport.areceive(timeout=1)
        assert isinstance(p, ProvisionChangedMessage)
        assert (
            p.status == ProvisionStatus.ACTIVE
        ), f"The provision should be active {p.message}"

        await transport.adelay(
            Assignation(
                provision="1",
                assignation="1",
                args=[[1]],
                kwargs={"name": {"hallo": 1}},
            )
        )

        await agent.astep()

        a = await transport.areceive(timeout=1)

        assert isinstance(a, AssignationChangedMessage)
        assert (
            a.status == AssignationStatus.ASSIGNED
        ), f"The assignaiton should be assigned {a.message}"

        a = await transport.areceive(timeout=1)
        assert isinstance(a, AssignationChangedMessage)
        assert (
            a.status == AssignationStatus.YIELD
        ), f"The assignaiton should have returned {a.message}"
        assert a.returns == [
            "tested",
            {"peter": 6},
        ], f"The provision should have returned {a.message}"

        await transport.adelay(
            Unassignation(
                provision="1",
                assignation="1",
            )
        )

        await agent.astep()

        a = await transport.areceive(timeout=1)
        assert isinstance(a, AssignationChangedMessage)
        assert (
            a.status == AssignationStatus.CANCELLED
        ), f"The assignaiton should have been cancelled {a.message}"


async def test_complex_agent_gen_provision_cancellation(
    complex_definition_registry_async,
):

    mockapp = MockApp(
        arkitekt=MockArkitekt(
            definition_registry=complex_definition_registry_async,
        )
    )

    transport: MockAgentTransport = mockapp.arkitekt.agent.transport
    agent: Agent = mockapp.arkitekt.agent

    async with mockapp:

        await agent.astart()

        await transport.adelay(Provision(provision="1", template="1"))
        await agent.astep()

        p = await transport.areceive(timeout=1)
        assert isinstance(p, ProvisionChangedMessage)
        assert (
            p.status == ProvisionStatus.PROVIDING
        ), f"First provision should be providing {p.message}"

        p = await transport.areceive(timeout=1)
        assert isinstance(p, ProvisionChangedMessage)
        assert (
            p.status == ProvisionStatus.ACTIVE
        ), f"The provision should be active {p.message}"

        await transport.adelay(
            Assignation(
                provision="1",
                assignation="1",
                args=[[1]],
                kwargs={"name": {"hallo": 1}},
            )
        )

        await agent.astep()

        a = await transport.areceive(timeout=1)

        assert isinstance(a, AssignationChangedMessage)
        assert (
            a.status == AssignationStatus.ASSIGNED
        ), f"The assignaiton should be assigned {a.message}"

        a = await transport.areceive(timeout=1)
        assert isinstance(a, AssignationChangedMessage)
        assert (
            a.status == AssignationStatus.YIELD
        ), f"The assignaiton should have returned {a.message}"
        assert a.returns == [
            "tested",
            {"peter": 6},
        ], f"The provision should have returned {a.message}"

        await transport.adelay(
            Unprovision(
                provision="1",
            )
        )

        await agent.astep()

        p = await transport.areceive(timeout=1)
        assert isinstance(p, ProvisionChangedMessage)
        assert (
            p.status == ProvisionStatus.CANCELING
        ), f"The assignaiton should have been cancelled {a.message}"

        a = await transport.areceive(timeout=1)
        assert isinstance(a, AssignationChangedMessage)
        assert (
            a.status == AssignationStatus.CANCELLED
        ), f"The assignaiton should have been cancelled {a.message}"

        p = await transport.areceive(timeout=1)
        assert isinstance(p, ProvisionChangedMessage)
        assert (
            p.status == ProvisionStatus.CANCELLED
        ), f"The assignaiton should have been cancelled {a.message}"
