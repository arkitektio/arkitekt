@pytest.fixture
def mock_app_provision_another_stateful_context(stateful_mikro_rath):

    app = MockApp(additional_contexts=[stateful_mikro_rath])

    @app.register()
    async def hallo_world(i: IdentifiableSerializableObject) -> str:
        """Hallo World

        Hallo world is a mini function

        Args:
            i (int): My little poney

        Returns:
            str: A nother little poney in string
        """
        print("oINOINOINOINOIN")
        print(
            await aquery_current_mikro(
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


async def test_app_provision_with_more_stateful_context(
    mock_app_provision_another_stateful_context: MockApp,
):
    transport: MockAgentTransport = (
        mock_app_provision_another_stateful_context.agent.transport
    )
    ptransport: MockPostmanTransport = (
        mock_app_provision_another_stateful_context.postman.transport
    )

    async with mock_app_provision_another_stateful_context:

        await transport.delay(Provision(template="1", provision="1", args=[1]))

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

        a = await transport.receive(timeout=1)
        assert isinstance(a, AssignationChangedMessage)
        assert (
            a.status == AssignationStatus.ASSIGNED
        ), f"The assignaiton should be assigned {a.message}"

        print("We are the best :)")

        a = await transport.receive(timeout=2)
        assert isinstance(a, AssignationChangedMessage)
        assert (
            a.status == AssignationStatus.RETURNED
        ), f"The assignaiton should have returned {a.message}"
        assert a.returns == ["678"], f"The provision should have returned {a.message}"

        print("nananana")