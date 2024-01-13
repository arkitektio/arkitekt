from click.testing import CliRunner
import pytest
from arkitekt.cli.main import cli


@pytest.fixture
def initialized_app_cli_runner():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "init",
                "--identifier",
                "arkitekt",
                "--version",
                "0.0.1",
                "--author",
                "arkitek",
                "--template",
                "simple",
                "--scopes",
                "read",
                "--scopes",
                "write",
                "--requirements",
                "gpu",
            ],
        )
        assert result.exit_code == 0, result.output
        yield runner



@pytest.fixture
def deployed_app():
    from arkitekt.deployed import deployed

    deployment = deployed("paper", "com.example.test")
    with deployment:
        yield deployment