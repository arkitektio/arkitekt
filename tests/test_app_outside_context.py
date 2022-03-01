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
from arkitekt import Arkitekt

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


@pytest.fixture
def mock_app_provision_another_stateful_context():

    app = MockApp()

    @app.register()
    def hallo_world(i: IdentifiableSerializableObject) -> str:
        """Hallo World

        Hallo world is a mini function

        Args:
            i (int): My little poney

        Returns:
            str: A nother little poney in string
        """
        print(threading.current_thread())
        print(
            query_current_mikro(
                """query ($package: String!, $interface: String!) {
                    node(package: $package, interface: $interface) {
                    id
                    }
                } 
            """,
                {"package": "mock", "interface": "node"},
            )
        )

        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! here")

        return str(i.number)

    return app


def test_app_provision_with_more_stateful_context():

    stateful_mikro_rath = StatefulMikroRath()

    with Koil():

        stateful_mikro_rath.connect()

        app = MockApp()

        @app.register()
        def hallo_world(i: IdentifiableSerializableObject) -> str:
            """Hallo World

            Hallo world is a mini function

            Args:
                i (int): My little poney

            Returns:
                str: A nother little poney in string
            """
            print(threading.current_thread())

            with stateful_mikro_rath:
                stateful_mikro_rath.execute(
                    """query ($package: String!, $interface: String!) {
                        node(package: $package, interface: $interface) {
                        id
                        }
                    } """,
                    variables={"package": "mock", "interface": "node"},
                )

            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! here")

            return str(i.number)

        transport: MockAgentTransport = app.agent.transport
        ptransport: MockPostmanTransport = app.postman.transport

        with app:

            transport.sync_delay(Provision(template="1", provision="1", args=[1]))

            p = transport.sync_receive(timeout=1)
            assert isinstance(p, ProvisionChangedMessage)
            assert (
                p.status == ProvisionStatus.PROVIDING
            ), f"First provision should be providing {p.message}"

            p = transport.sync_receive(timeout=1)
            assert isinstance(p, ProvisionChangedMessage)
            assert (
                p.status == ProvisionStatus.ACTIVE
            ), f"The provision should be active {p.message}"

            transport.sync_delay(
                Assignation(provision="1", assignation="1", args=[678])
            )

            a = transport.sync_receive(timeout=1)
            assert isinstance(a, AssignationChangedMessage)
            assert (
                a.status == AssignationStatus.ASSIGNED
            ), f"The assignaiton should be assigned {a.message}"

            print("We are the best :)")

            a = transport.sync_receive(timeout=2)
            assert isinstance(a, AssignationChangedMessage)
            assert (
                a.status == AssignationStatus.RETURNED
            ), f"The assignaiton should have returned {a.message}"
            assert a.returns == [
                "678"
            ], f"The provision should have returned {a.message}"

            print("nananana")
