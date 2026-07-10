"""Tests for the non-TTY interactive guard (``require_interactive``).

Every prompt site in the CLI is fronted by ``require_interactive`` so that a
non-interactive run (CI, a pipe) fails fast with guidance instead of blocking on
stdin forever. The autouse ``_assume_interactive`` fixture (see
``tests/conftest.py``) makes the CLI look interactive by default; these tests
patch ``is_interactive`` back to ``False`` to exercise the guard.
"""

import tempfile
from unittest.mock import patch

import pytest
import typer
from click.testing import CliRunner

from arkitekt_next.cli.interactive import require_interactive
from arkitekt_next.cli.main import cli

INTERACTIVE = "arkitekt_next.cli.interactive.is_interactive"


def test_require_interactive_is_noop_when_tty():
    with patch(INTERACTIVE, return_value=True):
        require_interactive("Something", hint="do X")  # must not raise


def test_require_interactive_raises_when_not_tty(capsys):
    with patch(INTERACTIVE, return_value=False):
        # cli_error prints the guidance to stderr, then raises typer.Exit(1).
        with pytest.raises(typer.Exit):
            require_interactive("The wizard", hint="Pass --template instead.")

    message = capsys.readouterr().err
    assert "The wizard" in message
    assert "Pass --template instead." in message


def test_coord_init_wizard_aborts_without_tty():
    """`coord init` with no template drops into the wizard -> guarded on non-TTY."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as d, patch(INTERACTIVE, return_value=False):
        result = runner.invoke(cli, ["--work-dir", d, "coord", "init"])

    assert result.exit_code != 0
    assert "interactive terminal" in result.output


def test_mesh_leave_aborts_without_tty_and_without_yes():
    """`mesh leave` without --yes must not block on the confirm in a non-TTY."""
    runner = CliRunner()
    with patch("arkitekt_next.cli.commands.mesh.main.shutil.which", return_value="/usr/bin/tailscale"), \
         patch(INTERACTIVE, return_value=False), \
         patch("arkitekt_next.cli.commands.mesh.main.subprocess.run") as mock_run:
        result = runner.invoke(cli, ["mesh", "leave"])

    assert result.exit_code != 0
    assert "interactive terminal" in result.output
    # It aborted before touching tailscale.
    mock_run.assert_not_called()
