import threading
import pytest
from rath.links import compose, ShrinkingLink, DictingLink
from rath.links.testing.mock import AsyncMockLink
from arkitekt.agents.transport.protocols.agent_json import (
    AssignationChangedMessage,
    ProvisionChangedMessage,
)
from arkitekt.api.schema import AssignationStatus, ProvisionStatus, afind
from arkitekt.messages import T, Assignation, Provision
from tests.mocks import (
    ArkitektMockResolver,
    MikroRath,
    MockApp,
    StatefulMikroRath,
    aquery_current_mikro,
    query_current_mikro,
)
from arkitekt.rath import ArkitektRath

from arkitekt.definition.registry import DefinitionRegistry, register
from arkitekt.structures.registry import StructureRegistry, register_structure
from arkitekt.agents.stateful import StatefulAgent
from arkitekt.agents.transport.mock import MockAgentTransport
import asyncio
from arkitekt.actors.functional import FunctionalFuncActor
from arkitekt.actors.actify import actify
from tests.structures import (
    IdentifiableSerializableObject,
    SecondSerializableObject,
    SerializableObject,
)
from rath.rath import Rath
from koil import Koil
from arkitekt.postmans.transport.mock import MockPostmanTransport


@pytest.fixture
def mock_app():

    structure_registry = StructureRegistry()
    definition_registry = DefinitionRegistry()

    app = MockApp(structure_registry, definition_registry)

    @app.register(structure_registry=structure_registry)
    async def hallo_world(i: IdentifiableSerializableObject) -> str:
        """Hallo World

        Hallo world is a mini function

        Args:
            i (int): My little poney

        Returns:
            str: A nother little poney in string
        """
        return str(i.number)

    return app


@pytest.fixture()
def mikro_rath():
    return MikroRath()


@pytest.fixture()
def stateful_mikro_rath():
    return StatefulMikroRath()


async def test_app_basic(mock_app: MockApp):
    transport: MockAgentTransport = mock_app.agent.transport
    ptransport: MockPostmanTransport = mock_app.postman.transport

    async with mock_app as app:
        await app.agent.astart()

        await transport.delay(Provision(template="1", provision="1", args=[1]))
        await app.agent.astep()

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

        await transport.delay(Assignation(provision="1", assignation="1", args=[678]))

        await app.agent.astep()

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
        assert a.returns == ["678"], f"The provision should have returned {a.message}"


@pytest.fixture
def mock_app_provision():

    structure_registry = StructureRegistry()
    definition_registry = DefinitionRegistry()

    app = MockApp(structure_registry, definition_registry)

    async def provide_node(provision, template):
        return {"node": await afind(package="mock", interface="node")}

    @app.register(structure_registry=structure_registry, on_provide=provide_node)
    def hallo_world(i: IdentifiableSerializableObject) -> str:
        """Hallo World

        Hallo world is a mini function

        Args:
            i (int): My little poney

        Returns:
            str: A nother little poney in string
        """

        return str(i.number)

    return app


async def test_app_provision(mock_app_provision: MockApp):
    transport: MockAgentTransport = mock_app_provision.agent.transport
    ptransport: MockPostmanTransport = mock_app_provision.postman.transport

    async with mock_app_provision as app:
        await app.agent.astart()

        await transport.delay(Provision(template="1", provision="1", args=[1]))
        await app.agent.astep()

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

        await transport.delay(Assignation(provision="1", assignation="1", args=[678]))
        await app.agent.astep()

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
        assert a.returns == ["678"], f"The provision should have returned {a.message}"


@pytest.fixture
def mock_app_provision_another_context(mikro_rath):

    app = MockApp(additional_contexts=[mikro_rath])

    @app.register()
    def hallo_world(i: IdentifiableSerializableObject) -> str:
        """Hallo World

        Hallo world is a mini function

        Args:
            i (int): My little poney

        Returns:
            str: A nother little poney in string
        """
        print("nananan")
        print(
            query_current_mikro(
                """ query ($package: String!, $interface: String!) {
                    node(package: $package, interface: $interface) {
                    id
                    }
                } 
            """,
                {"package": "mock", "interface": "node"},
            )
        )
        print("nasoinaoianon")
        return str(i.number)

    return app


async def test_app_provision_with_more_context(
    mock_app_provision_another_context: MockApp,
):
    transport: MockAgentTransport = mock_app_provision_another_context.agent.transport
    ptransport: MockPostmanTransport = (
        mock_app_provision_another_context.postman.transport
    )

    async with mock_app_provision_another_context as app:
        await app.agent.astart()

        await transport.delay(Provision(template="1", provision="1", args=[1]))
        await app.agent.astep()

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

        await transport.delay(Assignation(provision="1", assignation="1", args=[678]))
        await app.agent.astep()

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
        assert a.returns == ["678"], f"The provision should have returned {a.message}"


async def test_app_provision_with_more_context_duo(
    mock_app_provision_another_context: MockApp,
):
    transport: MockAgentTransport = mock_app_provision_another_context.agent.transport
    ptransport: MockPostmanTransport = (
        mock_app_provision_another_context.postman.transport
    )

    async with mock_app_provision_another_context as app:

        await app.agent.astart()
        await transport.delay(Provision(template="1", provision="1", args=[1]))
        await app.agent.astep()

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

        await transport.delay(Assignation(provision="1", assignation="1", args=[678]))
        await app.agent.astep()

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
        assert a.returns == ["678"], f"The provision should have returned {a.message}"


async def test_app_provision_with_more_context_and_again(
    mock_app_provision_another_context: MockApp,
):

    transport: MockAgentTransport = mock_app_provision_another_context.agent.transport
    ptransport: MockPostmanTransport = (
        mock_app_provision_another_context.postman.transport
    )

    async with mock_app_provision_another_context as app:
        await app.agent.astart()

        await transport.delay(Provision(template="1", provision="1", args=[1]))
        await app.agent.astep()
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

        await transport.delay(Assignation(provision="1", assignation="1", args=[678]))
        await app.agent.astep()
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
        assert a.returns == ["678"], f"The provision should have returned {a.message}"
