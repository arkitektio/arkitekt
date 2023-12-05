from click.testing import CliRunner
from arkitekt.cli.main import cli
import os
from arkitekt.cli.io import load_manifest_yaml
import pytest


@pytest.fixture
def initialized_app_cli_runner():
    runner = CliRunner()
    with runner.isolated_filesystem() as td:
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
            ],
        )
        assert result.exit_code == 0, result.output
        yield runner


@pytest.mark.cli
def test_init():
    runner = CliRunner()
    with runner.isolated_filesystem() as td:
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
            ],
        )

        arkitekt_folder = os.path.join(td, ".arkitekt")

        assert result.exit_code == 0
        assert os.path.exists(arkitekt_folder)
        assert os.path.exists(os.path.join(arkitekt_folder, "manifest.yaml"))

        manifest = load_manifest_yaml(os.path.join(arkitekt_folder, "manifest.yaml"))
        assert manifest.identifier == "arkitekt"
        assert manifest.version == "0.0.1"
        assert manifest.author == "arkitek"
        assert manifest.scopes == ["read", "write"]


@pytest.mark.cli
def test_no_init():
    runner = CliRunner()
    with runner.isolated_filesystem() as td:
        result = runner.invoke(
            cli,
            [
                "init",
            ],
        )
        # Second time
        result = runner.invoke(
            cli,
            [
                "init",
            ],
        )

        assert result.exit_code == 1
        assert "Do you want to overwrite" in result.output


@pytest.mark.cli
def test_with_overwrite():
    runner = CliRunner()
    with runner.isolated_filesystem() as td:
        result = runner.invoke(
            cli,
            [
                "init",
            ],
        )
        # Second time
        result = runner.invoke(
            cli,
            [
                "init",
                "--overwrite-manifest",
            ],
        )

        assert result.exit_code == 0


@pytest.mark.cli
def test_not_yet_initialized():
    runner = CliRunner()
    with runner.isolated_filesystem() as td:
        result = runner.invoke(
            cli,
            ["manifest", "scopes", "add", "write"],
        )

        assert result.exit_code == 1
        assert "No manifest found" in result.output
