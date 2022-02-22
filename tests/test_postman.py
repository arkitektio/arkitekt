import pytest
from rath.links import compose, ShrinkingLink, DictingLink
from rath.links.testing.mock import AsyncMockLink
from tests.mocks import ArkitektQueryResolver, ArkitektMutationResolver
from arkitekt import Arkitekt

from arkitekt.definition.registry import DefinitionRegistry, register
from arkitekt.structures.registry import StructureRegistry
from arkitekt.postmans.transport.mock import MockPostmanTransport
from arkitekt.postmans.stateful import StatefulPostman
from arkitekt.postmans.utils import use
import asyncio
from arkitekt.api.schema import afind


@pytest.fixture
def arkitekt_client():

    link = compose(
        ShrinkingLink(),
        DictingLink(),  # after the shrinking so we can override the dicting
        AsyncMockLink(
            query_resolver=ArkitektQueryResolver(),
            mutation_resolver=ArkitektMutationResolver(),
        ),
    )

    return Arkitekt(link)


async def test_postman(mock_postman: StatefulPostman, arkitekt_client):

    await mock_postman.aconnect()

    node = await afind(package="mock", interface="run_maboy", arkitekt=arkitekt_client)

    async def test_function():
        async with use(node, postman=mock_postman) as res:
            return await res.assign(a=1, b=2)

    returns = await asyncio.wait_for(test_function(), timeout=2)
    assert returns == [], "x should be empty"


@pytest.fixture
def mock_postman(arkitekt_client):

    transport = MockPostmanTransport()

    postman = StatefulPostman(
        transport=transport,
    )

    return postman
