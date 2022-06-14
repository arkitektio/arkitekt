import pytest
from fakts import Fakts
from fakts.grants import YamlGrant
from herre.fakts import FaktsHerre
from arkitekt.api.schema import adefine
from herre.fakts.herre import FaktsHerre
from .integration.utils import wait_for_http_response
from .utils import build_relative
from testcontainers.compose import DockerCompose
from arkitekt.app import ArkitektApp
from arkitekt.definition.define import prepare_definition
from .funcs import complex_karl
from herre.fakts import FaktsHerre
from fakts.grants.remote.claim import ClaimGrant
from fakts.grants.remote.base import StaticDiscovery

@pytest.mark.integration
@pytest.fixture(scope="session")
def environment():
    with DockerCompose(
        filepath=build_relative("integration"),
        compose_file_name="docker-compose.yaml",
    ) as compose:
        wait_for_http_response("http://localhost:8019/ht", max_retries=5)
        wait_for_http_response("http://localhost:8098/ht", max_retries=5)
        yield


@pytest.mark.integration
@pytest.fixture
def app():

    return ArkitektApp(
        fakts=Fakts(
            grant=ClaimGrant(
                client_id="DSNwVKbSmvKuIUln36FmpWNVE2KrbS2oRX0ke8PJ",
                client_secret="Gp3VldiWUmHgKkIxZjL2aEjVmNwnSyIGHWbQJo6bWMDoIUlBqvUyoGWUWAe6jI3KRXDOsD13gkYVCZR0po1BLFO9QT4lktKODHDs0GyyJEzmIjkpEOItfdCC4zIa3Qzu",
                graph="localhost",
                discovery=StaticDiscovery(base_url="http://localhost:8019/f/"),
            ),
            force_refresh=True,
        ),
        herre=FaktsHerre(no_temp=True),
    )


@pytest.mark.integration
async def test_definining(app: ArkitektApp, environment):

    async with app:
        functional_definition = prepare_definition(
            complex_karl, structure_registry=app.arkitekt.structure_registry
        )

        node = await adefine(functional_definition)
        assert node.id, "Node is None"
        assert node.package == "tests", "Should be resolving to tests (the app name)"
