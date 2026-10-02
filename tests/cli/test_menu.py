"""The root menu follows the folder: an app's commands where there is an app,
`create` where there is none. Nothing is taken away, only left off the list."""

import pytest
from typer.testing import CliRunner

from arkitekt.cli.app import APP_MENU, BARE_MENU
from arkitekt.cli.main import cli_app
from arkitekt.cli.target import has_app


def _listed(output: str) -> list[str]:
    """The commands the help lists, in order."""
    commands = output.split("Commands", 1)[1]
    names = []
    for line in commands.splitlines():
        words = line.strip("│ ").split()
        if line.startswith("│") and words:
            names.append(words[0])
    return names


@pytest.mark.parametrize("order", [("--work-dir", "{}", "--help"), ("--help", "--work-dir", "{}")])
def test_a_folder_with_an_app_lists_its_commands(app_dir, order):
    result = CliRunner().invoke(cli_app, [part.format(app_dir) for part in order])

    assert result.exit_code == 0, result.output
    assert _listed(result.output) == list(APP_MENU)
    assert "app.py in this folder" in result.output


@pytest.mark.parametrize("order", [("--work-dir", "{}", "--help"), ("--help", "--work-dir", "{}")])
def test_a_folder_without_an_app_lists_create(tmp_path, order):
    result = CliRunner().invoke(cli_app, [part.format(tmp_path) for part in order])

    assert result.exit_code == 0, result.output
    assert _listed(result.output) == list(BARE_MENU)
    assert "arkitekt create" in result.output


def test_an_app_is_a_target_file_that_mentions_arkitekt(tmp_path, monkeypatch):
    monkeypatch.delenv("ARKITEKT_APP", raising=False)
    assert has_app(str(tmp_path)) is None

    (tmp_path / "app.py").write_text("print('just a script')\n")
    assert has_app(str(tmp_path)) is None

    (tmp_path / "app.py").write_text("from arkitekt import App\n")
    assert has_app(str(tmp_path)) == str(tmp_path / "app.py")


def test_the_app_is_found_without_running_it(tmp_path, monkeypatch):
    """What the help lists must not depend on importing the user's code."""
    monkeypatch.delenv("ARKITEKT_APP", raising=False)
    (tmp_path / "app.py").write_text("import arkitekt\nraise SystemExit('imported')\n")

    result = CliRunner().invoke(cli_app, ["--work-dir", str(tmp_path), "--help"])

    assert result.exit_code == 0, result.output
    assert _listed(result.output) == list(APP_MENU)


def test_the_target_from_the_environment_names_the_app(tmp_path, monkeypatch):
    (tmp_path / "main.py").write_text("from arkitekt import App\n")

    monkeypatch.setenv("ARKITEKT_APP", "main")
    assert has_app(str(tmp_path)) == str(tmp_path / "main.py")


def test_a_command_off_the_menu_still_runs_and_says_what_is_missing(tmp_path):
    result = CliRunner().invoke(cli_app, ["--work-dir", str(tmp_path), "run", "prod"])

    assert result.exit_code != 0
    assert "Could not find the app module 'app'" in result.output
    assert "arkitekt create" in result.output


def test_create_is_off_the_app_menu_but_still_there(app_dir):
    result = CliRunner().invoke(cli_app, ["--work-dir", str(app_dir), "create", "--help"])

    assert result.exit_code == 0, result.output


def test_init_is_gone(tmp_path):
    result = CliRunner().invoke(cli_app, ["--work-dir", str(tmp_path), "init"])

    assert result.exit_code != 0
    assert "No such command" in result.output
