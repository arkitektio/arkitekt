from arkitekt.agents.transport.protocols.agent_json import (
    AssignationChangedMessage,
    ProvisionChangedMessage,
)
from arkitekt.api.schema import AssignationStatus, ProvisionStatus
from arkitekt.messages import Assignation, Provision

from arkitekt.structures.registry import StructureRegistry
from tests.mocks import MockArkitekt, MockComposedApp, query_current_mikro
from tests.structures import (
    IdentifiableSerializableObject,
)


async def test_app_provision_with_more_stateful_context():

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
        query_current_mikro(
            """query ($package: String!, $interface: String!) {
                    node(package: $package, interface: $interface) {
                    id
                    }
                } 
            """,
            {"package": "mock", "interface": "node"},
        )

        return str(i.number)

    transport = app.arkitekt.agent.transport
    ptransport = app.arkitekt.agent.transport
    agent = app.arkitekt.agent

    async with app:

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
        assert a.returns == [
            "678"
        ], f"The provision should have returned 678 not {a.returns}"

        print("nananana")
