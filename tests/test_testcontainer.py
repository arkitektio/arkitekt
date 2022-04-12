import pytest
from testcontainers.compose import DockerCompose
from .utils import build_relative

@pytest.mark.integration
def test_environment():
    with DockerCompose(
        filepath=build_relative("integration"),
        compose_file_name="hello-compose.yaml",
    ) as compose:
        assert True, "We should be here"
