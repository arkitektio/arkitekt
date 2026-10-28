"""The plugin commands take the app's identity from its image, and keep its target.

A build records the identifier/version/author/scopes/logo the built image reports
(what ``app_manifest`` makes of its App, inside the container) plus the target that
finds it, so the image is inspected and staged on that same app. The app is never
imported on the building machine. Nothing here needs docker: the subprocess
boundary is mocked.
"""

import json
from unittest.mock import patch

from typer.testing import CliRunner

from arkitekt import App
from arkitekt.app.spec import app_manifest
from arkitekt.cli.commands.plugin.build import inspect_all
from arkitekt.cli.commands.plugin.io import get_builds
from arkitekt_spec import UNKNOWN_AUTHOR, AppManifest, Inspection
from arkitekt.cli.commands.plugin.types import Build
from arkitekt.cli.main import cli_app
from arkitekt.cli.target import infer_package_manager


def test_an_image_reports_the_apps_identity_and_target():
    manifest = app_manifest(
        App(
            "com.x",
            "1.2.3",
            author="me",
            scopes=["mikro_read"],
            logo="http://l",
            description="What it is",
        ),
        entrypoint="main:api",
    )

    assert (manifest.identifier, manifest.version, manifest.author) == ("com.x", "1.2.3", "me")
    assert manifest.scopes == ["mikro_read", "openid"]
    assert manifest.description == "What it is"
    assert manifest.logo == "http://l"
    assert manifest.entrypoint == "main:api"


def test_an_app_without_an_author_is_recorded_as_unknown():
    assert app_manifest(App("com.x"), entrypoint="app").author == UNKNOWN_AUTHOR


def test_a_staged_build_runs_the_recorded_target():
    build = Build(
        build_run="run",
        build_id="image",
        manifest=app_manifest(App("com.x"), entrypoint="main:api"),
    )

    assert build.build_arkitekt_command("http://fakts") == [
        "arkitekt", "run", "prod", "--headless", "main:api", "--url", "http://fakts",
    ]


class _OkProc:
    returncode = 0

    def communicate(self, timeout=None):
        return (
            b"--START_AGENT--" + json.dumps({"implementations": []}).encode() + b"--END_AGENT--"
            b"--START_MANIFEST--" + json.dumps({"identifier": "com.x", "version": "1"}).encode()
            + b"--END_MANIFEST--",
            b"",
        )


def test_the_image_is_inspected_on_the_built_target():
    with patch("arkitekt.cli.commands.plugin.build.subprocess.Popen", return_value=_OkProc()) as popen:
        inspect_all("image", "http://fakts", "main:api")

    command = popen.call_args[0][0]
    assert "arkitekt inspect all main:api -mr" in command
    assert "--rm" in command  # the inspection's container is not left behind


def _flavour_without_an_app(tmp_path):
    """A flavour, and no app module at all: the image is the only place the app is."""
    result = CliRunner().invoke(cli_app, [
        "--work-dir", str(tmp_path), "plugin", "init", "--no-multi-arch", "--arkitekt-version", "0.0.1",
    ], input="n\n")
    assert result.exit_code == 0, result.output


def test_a_build_records_who_the_image_says_it_is_without_importing_the_app(tmp_path):
    _flavour_without_an_app(tmp_path)
    reported = AppManifest(identifier="from.the.image", version="9.9.9", entrypoint="main:api")

    with patch("arkitekt.cli.commands.plugin.build.build_flavour", return_value="image"), patch(
        "arkitekt.cli.commands.plugin.build.inspect_build", return_value=(Inspection(), reported)
    ) as inspected:
        result = CliRunner().invoke(cli_app, ["--work-dir", str(tmp_path), "plugin", "build", "main:api"])

    assert result.exit_code == 0, result.output
    assert inspected.call_args.args[2] == "main:api"
    (build,) = get_builds(base_dir=str(tmp_path)).values()
    assert build.manifest == reported


def test_a_build_that_is_not_inspected_is_not_recorded(tmp_path):
    _flavour_without_an_app(tmp_path)

    with patch("arkitekt.cli.commands.plugin.build.build_flavour", return_value="image"), patch(
        "arkitekt.cli.commands.plugin.build.inspect_build"
    ) as inspected:
        result = CliRunner().invoke(cli_app, ["--work-dir", str(tmp_path), "plugin", "build", "--no-inspect"])

    assert result.exit_code == 0, result.output
    assert "Not recorded" in result.output
    inspected.assert_not_called()
    assert not (tmp_path / ".arkitekt" / "builds.yaml").exists()


def test_the_package_manager_is_inferred_from_the_lockfile(tmp_path):
    assert infer_package_manager(str(tmp_path)) == "pip"
    (tmp_path / "uv.lock").write_text("")
    assert infer_package_manager(str(tmp_path)) == "uv"


def test_plugin_init_picks_the_uv_image_for_a_uv_project_without_loading_the_app(tmp_path):
    """No app module here at all: only the devcontainer needs the app."""
    (tmp_path / "uv.lock").write_text("")

    result = CliRunner().invoke(cli_app, [
        "--work-dir", str(tmp_path), "plugin", "init", "--arkitekt-version", "0.0.1",
    ], input="n\n")

    assert result.exit_code == 0, result.output
    dockerfile = (tmp_path / ".arkitekt" / "flavours" / "vanilla" / "Dockerfile").read_text()
    assert "uv sync" in dockerfile


def test_plugin_init_names_the_devcontainer_after_the_app(app_dir, monkeypatch):
    monkeypatch.chdir(app_dir)  # the devcontainer is written relative to the cwd

    result = CliRunner().invoke(cli_app, [
        "--work-dir", str(app_dir), "plugin", "init", "--devcontainer", "--arkitekt-version", "0.0.1",
    ])

    assert result.exit_code == 0, result.output
    devcontainer = json.loads((app_dir / ".devcontainer" / "vanilla" / "devcontainer.json").read_text())
    assert devcontainer["name"] == "com.test.app vanilla Devcontainer"


def test_plugin_init_devcontainer_without_an_app_is_a_clean_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli_app, [
        "--work-dir", str(tmp_path), "plugin", "init", "--devcontainer", "--arkitekt-version", "0.0.1",
    ])

    assert result.exit_code != 0
    assert "Could not find the app module 'app'" in result.output


def test_an_app_asks_for_what_its_services_clients_need():
    from arkitekt_spec.declare.app import AppRegistry

    class Client:
        """A client whose generated part says what its operations need."""

        __scopes__ = ("mikro_write", "mikro_read")

    registry = AppRegistry()

    @registry.service()
    def mikro() -> Client:
        """Talks to mikro."""
        return Client()

    app = App("com.x", "1.0", services=[mikro])
    assert app.scopes == ["mikro_read", "mikro_write", "openid"]
    assert app.manifest.scopes == ["mikro_read", "mikro_write", "openid"]
    assert App("com.y", "1.0", services=[mikro], scopes=["kabinet_deploy"]).scopes == ["kabinet_deploy", "mikro_read", "mikro_write", "openid"]
