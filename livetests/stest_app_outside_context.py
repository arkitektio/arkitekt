import threading
from arkitekt.agents.transport.protocols.agent_json import (
    AssignationChangedMessage,
    ProvisionChangedMessage,
)
from arkitekt.api.schema import AssignationStatus, ProvisionStatus
from arkitekt.messages import Assignation, Provision
from tests.mocks import (
    MockArkitekt,
    MockComposedApp,
)

from arkitekt.structures.registry import StructureRegistry
from arkitekt.agents.stateful import StatefulAgent
from arkitekt.agents.transport.mock import MockAgentTransport
from tests.structures import (
    IdentifiableSerializableObject,
)
from arkitekt.postmans.transport.mock import MockPostmanTransport


def test_app_provision_with_more_stateful_context_sync():

    app = MockComposedApp(
        arkitekt=MockArkitekt(
            structure_registry=StructureRegistry(allow_auto_register=True),
        )
    )

    @app.arkitekt.register()
    def hallo_world(i: IdentifiableSerializableObject) -> str:
        """Hallo World

        Hallo world is a mini function

        Args:
            i (int): My little poney

        Returns:
            str: A nother little poney in string
        """
        print(threading.current_thread())

        app.additional_rath.execute(
            """query ($package: String!, $interface: String!) {
                node(package: $package, interface: $interface) {
                id
                }
            } """,
            variables={"package": "mock", "interface": "node"},
        )

        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! here")

        return str(i.number)

    transport: MockAgentTransport = app.arkitekt.agent.transport
    ptransport: MockPostmanTransport = app.arkitekt.postman.transport
    agent: StatefulAgent = app.arkitekt.agent

    with app:

        agent.start()

        transport.sync_delay(Provision(template="1", provision="1", args=[1]))
        agent.step()

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

        transport.sync_delay(Assignation(provision="1", assignation="1", args=[678]))
        agent.step()

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
        assert a.returns == ["678"], f"The provision should have returned {a.message}"

        print("nananana")
