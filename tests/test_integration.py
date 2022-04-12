import pytest
from fakts import Fakts
from fakts.grants import YamlGrant

from arkitekt.api.schema import adefine
from .integration.utils import wait_for_http_response
from .utils import build_relative
from testcontainers.compose import DockerCompose
from arkitekt.app import ArkitektApp
from arkitekt.definition.define import prepare_definition
from .funcs import complex_karl

@pytest.mark.integration
@pytest.fixture(scope="session")
def environment():
    with DockerCompose(
        filepath=build_relative("integration"),
        compose_file_name="docker-compose.yaml",
    ) as compose:
        wait_for_http_response("http://localhost:8008/ht", max_retries=5)
        wait_for_http_response("http://localhost:8098/ht", max_retries=5)
        yield


@pytest.mark.integration
@pytest.fixture
def app():

    return ArkitektApp(
        fakts=Fakts(
            subapp="test",
            grants=[YamlGrant(filepath=build_relative("configs/test.yaml"))],
            force_refresh=True,
        )
    )



@pytest.mark.integration
async def test_get_random(app: ArkitektApp, environment):

    async with app:
        functional_definition = prepare_definition(
            complex_karl, structure_registry=app.arkitekt.structure_registry
        )

        node = await adefine(functional_definition)
        assert node, "Node is None"
