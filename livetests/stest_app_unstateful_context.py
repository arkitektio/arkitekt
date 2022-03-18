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
    MockApp,
    MockArkitekt,
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


async def test_app_basic_async_func(mock_app: MockApp):

    app = MockApp(
        arkitekt=MockArkitekt(
            structure_registry=StructureRegistry(allow_auto_register=True),
        )
    )

    @app.arkitekt.register()
    async def hallo_world(i: IdentifiableSerializableObject) -> str:
        """Hallo World

        Hallo world is a mini function

        Args:
            i (int): My little poney

        Returns:
            str: A nother little poney in string
        """
        return str(i.number)

    transport: MockAgentTransport = app.arkitekt.agent.transport
    ptransport: MockPostmanTransport = app.arkitekt.postman.transport
    agent = app.arkitekt.agent
    async with mock_app as app:
        await agent.astart()

        await transport.delay(Provision(template="1", provision="1", args=[1]))
        await agent.astep()

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

        await agent.astep()

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


async def test_app_provide_node_async(mock_app_provision: MockApp):

    app = MockApp(
        arkitekt=MockArkitekt(
            structure_registry=StructureRegistry(allow_auto_register=True),
        )
    )

    async def provide_node(provision, template):
        return {"node": await afind(package="mock", interface="node")}

    @app.arkitekt.register(on_provide=provide_node)
    async def hallo_world(i: IdentifiableSerializableObject) -> str:
        """Hallo World

        Hallo world is a mini function

        Args:
            i (int): My little poney

        Returns:
            str: A nother little poney in string
        """
        return str(i.number)

    transport: MockAgentTransport = app.arkitekt.agent.transport
    ptransport: MockPostmanTransport = app.arkitekt.postman.transport

    agent = app.arkitekt.agent

    async with mock_app_provision as app:
        await agent.astart()

        await transport.delay(Provision(template="1", provision="1", args=[1]))
        await agent.astep()

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
        await agent.astep()

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
