"""Tests for the non-TTY interactive guard (``require_tty``).

Every prompt site in the CLI is fronted by ``require_tty`` so that a
non-interactive run (CI, a pipe) fails fast with guidance instead of blocking on
stdin forever. The autouse ``_assume_interactive`` fixture (see
``tests/conftest.py``) makes the CLI look interactive by default; these tests
patch ``is_tty`` back to ``False`` to exercise the guard.
"""

from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from arkitekt.cli.tty import require_tty
from arkitekt.cli.main import cli_app

INTERACTIVE = "arkitekt.cli.tty.is_tty"


def test_require_tty_is_noop_when_tty():
    with patch(INTERACTIVE, return_value=True):
        require_tty("Something", hint="do X")  # must not raise


def test_require_tty_raises_when_not_tty(capsys):
    with patch(INTERACTIVE, return_value=False):
        # cli_error prints the guidance to stderr, then raises typer.Exit(1).
        with pytest.raises(typer.Exit):
            require_tty("The wizard", hint="Pass --template instead.")

    message = capsys.readouterr().err
    assert "The wizard" in message
    assert "Pass --template instead." in message


def test_mesh_leave_aborts_without_tty_and_without_yes():
    """`mesh leave` without --yes must not block on the confirm in a non-TTY."""
    runner = CliRunner()
    with patch("arkitekt.cli.commands.mesh.main.shutil.which", return_value="/usr/bin/tailscale"), \
         patch(INTERACTIVE, return_value=False), \
         patch("arkitekt.cli.commands.mesh.main.subprocess.run") as mock_run:
        result = runner.invoke(cli_app, ["mesh", "leave"])

    assert result.exit_code != 0
    assert "interactive terminal" in result.output
    # It aborted before touching tailscale.
    mock_run.assert_not_called()
