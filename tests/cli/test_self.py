import io
import json
import sys
from unittest.mock import patch

from click.testing import CliRunner

from arkitekt_next.cli.main import cli

MODULE = "arkitekt_next.cli.commands.self.upgrade"


def _pypi_payload(version: str) -> bytes:
    return json.dumps({"info": {"version": version}, "releases": {version: []}}).encode()


def _fake_urlopen(version: str):
    """Return a fake urlopen that yields a PyPI JSON payload for any package."""

    def _urlopen(url, timeout=None):
        return io.BytesIO(_pypi_payload(version))

    return _urlopen


def test_self_upgrade_pip_outdated():
    """An outdated package triggers a pip upgrade with the right command."""
    runner = CliRunner()
    with patch(f"{MODULE}.installed_version", return_value="1.0.0"), patch(
        f"{MODULE}.urllib.request.urlopen", _fake_urlopen("2.0.0")
    ), patch(f"{MODULE}.subprocess.run") as mock_run:
        result = runner.invoke(
            cli, ["self", "upgrade", "--package-manager", "pip", "--yes"]
        )
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0
        assert mock_run.call_count == 1
        command = mock_run.call_args[0][0]
        assert command[:4] == [sys.executable, "-m", "pip", "install"]
        assert "--upgrade" in command
        assert "arkitekt-next" in command


def test_self_upgrade_uv_outdated():
    """With uv selected, uv add --upgrade is used and uv presence is checked."""
    runner = CliRunner()
    with patch(f"{MODULE}.installed_version", return_value="1.0.0"), patch(
        f"{MODULE}.urllib.request.urlopen", _fake_urlopen("2.0.0")
    ), patch(f"{MODULE}.shutil.which", return_value="/usr/bin/uv"), patch(
        f"{MODULE}.subprocess.run"
    ) as mock_run:
        result = runner.invoke(
            cli, ["self", "upgrade", "--package-manager", "uv", "--yes"]
        )
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0
        assert mock_run.call_count == 1
        command = mock_run.call_args[0][0]
        assert command[:3] == ["uv", "add", "--upgrade"]
        assert "arkitekt-next" in command


def test_self_upgrade_uv_not_installed():
    """Selecting uv without uv installed raises a clear error."""
    runner = CliRunner()
    with patch(f"{MODULE}.installed_version", return_value="1.0.0"), patch(
        f"{MODULE}.urllib.request.urlopen", _fake_urlopen("2.0.0")
    ), patch(f"{MODULE}.shutil.which", return_value=None), patch(
        f"{MODULE}.subprocess.run"
    ) as mock_run:
        result = runner.invoke(
            cli, ["self", "upgrade", "--package-manager", "uv", "--yes"]
        )
        assert result.exit_code != 0
        assert "uv is not installed" in result.output
        assert mock_run.call_count == 0


def test_self_upgrade_up_to_date():
    """When installed == latest, nothing is upgraded."""
    runner = CliRunner()
    with patch(f"{MODULE}.installed_version", return_value="2.0.0"), patch(
        f"{MODULE}.urllib.request.urlopen", _fake_urlopen("2.0.0")
    ), patch(f"{MODULE}.subprocess.run") as mock_run:
        result = runner.invoke(
            cli, ["self", "upgrade", "--package-manager", "pip", "--yes"]
        )
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0
        assert "up to date" in result.output
        assert mock_run.call_count == 0


def test_self_upgrade_confirm_no_aborts():
    """Declining the confirmation prompt aborts without upgrading."""
    runner = CliRunner()
    with patch(f"{MODULE}.installed_version", return_value="1.0.0"), patch(
        f"{MODULE}.urllib.request.urlopen", _fake_urlopen("2.0.0")
    ), patch(f"{MODULE}.subprocess.run") as mock_run:
        result = runner.invoke(
            cli, ["self", "upgrade", "--package-manager", "pip"], input="n\n"
        )
        assert result.exit_code != 0  # aborted
        assert mock_run.call_count == 0
