import pytest

from .mocks import MockArkitektRath
from arkitekt.rath import ArkitektRath

from arkitekt.postmans.transport.mock import MockPostmanTransport
from arkitekt.postmans.stateful import StatefulPostman
from arkitekt.postmans.utils import use
import asyncio
from arkitekt.api.schema import afind


@pytest.fixture
def arkitekt_rath():

    return MockArkitektRath()


@pytest.fixture
def mock_postman():

    transport = MockPostmanTransport()

    postman = StatefulPostman(
        transport=transport,
    )

    return postman


async def test_postman(mock_postman, arkitekt_rath):

    async with arkitekt_rath:
        async with mock_postman:

            node = await afind(package="mock", interface="run_maboy")
            print(node)

            async def test_function():
                async with use(node) as res:
                    return await res.aassign(a=1, b=2)

            returns = await asyncio.wait_for(test_function(), timeout=2)

        assert returns == [], "x should be empty"
