import pytest
from rath.links import compose, ShrinkingLink, DictingLink
from rath.links.testing.mock import AsyncMockLink
from tests.mocks import ArkitektMockResolver
from arkitekt.rath import ArkitektRath

from arkitekt.definition.registry import DefinitionRegistry, register
from arkitekt.structures.registry import StructureRegistry
from arkitekt.postmans.transport.mock import MockPostmanTransport
from arkitekt.postmans.stateful import StatefulPostman
from arkitekt.postmans.utils import use
import asyncio
from arkitekt.api.schema import afind


@pytest.fixture
def arkitekt_rath():

    link = compose(
        ShrinkingLink(),
        DictingLink(),  # after the shrinking so we can override the dicting
        AsyncMockLink(
            query_resolver=ArkitektMockResolver(),
        ),
    )

    return ArkitektRath(link)


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

            async def test_function():
                async with use(node, postman=mock_postman) as res:
                    return await res.assign(a=1, b=2)

            returns = await asyncio.wait_for(test_function(), timeout=2)

        assert returns == [], "x should be empty"
