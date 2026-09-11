"""Tests for the ``mesh`` command group (join / cert).

`join` uses the mesh device-code flow: discover endpoints from the Fakts
well-known document, start a join, poll for a pre-auth key, then run
`tailscale up --authkey=…`. These tests mock the network boundary
(`_fetch_well_known`, `_mesh_start`, `_mesh_poll`) and `subprocess.run`.
"""

import asyncio
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import typer
from click.testing import CliRunner

from arkitekt.cli.main import cli
from arkitekt.cli.commands.mesh.main import TAILSCALE_UP_TIMEOUT_SECONDS

MESH = "arkitekt.cli.commands.mesh.main"

# A well-known doc advertising the mesh device-code endpoints.
WELL_KNOWN = {
    "name": "F",
    "mesh_device_code_start": "http://fakts.example/f/meshstart/",
    "mesh_challenge_url": "http://fakts.example/f/meshchallenge/",
    "mesh_configure": "http://fakts.example/meshconfigure",
    "mesh_coord_url": "https://coord.example",
}

# The granted challenge payload.
GRANTED = {
    "status": "granted",
    "ionscale_auth_key": "tskey-abc123",
    "ionscale_coord_url": "https://coord.example",
    "machine_name": "my-box",
}


def _ok(returncode: int = 0):
    return SimpleNamespace(returncode=returncode)


@pytest.fixture(autouse=True)
def _tailscale_installed():
    """Pretend tailscale is installed for every test unless overridden."""
    with patch(f"{MESH}.shutil.which", return_value="/usr/bin/tailscale"):
        yield


def _patch_flow(granted=GRANTED, well_known=WELL_KNOWN):
    """Patch the whole device-code flow boundary. Returns the ExitStack-like tuple."""
    return (
        patch(f"{MESH}._fetch_well_known", return_value=well_known),
        patch(f"{MESH}._mesh_start", return_value=("CODE123", "CHALLENGE456")),
        patch(f"{MESH}._mesh_poll", return_value=granted),
    )


def test_mesh_group_registered():
    result = CliRunner().invoke(cli, ["mesh", "--help"])
    assert result.exit_code == 0
    assert "join" in result.output
    assert "cert" in result.output


def test_join_help_has_device_code_options_and_no_force_reauth():
    result = CliRunner().invoke(cli, ["mesh", "join", "--help"])
    assert result.exit_code == 0
    for opt in ("--name", "--description", "--ephemeral", "--tag", "--expiration"):
        assert opt in result.output
    assert "--open-browser" in result.output
    # The old force-reauth *option* (and its disconnect warning) is gone.
    assert "disconnect" not in result.output


def test_join_runs_full_device_code_flow():
    runner = CliRunner()
    p_fetch, p_start, p_poll = _patch_flow()
    with p_fetch, p_start as mock_start, p_poll as mock_poll, patch(
        f"{MESH}.subprocess.run", return_value=_ok()
    ) as mock_run:
        result = runner.invoke(
            cli,
            ["mesh", "join", "-u", "http://fakts.example", "--no-open-browser", "-n", "req-name"],
        )

    assert result.exit_code == 0, result.output
    # meshstart payload carries the requested name.
    assert mock_start.call_args.args[1]["requested_machine_name"] == "req-name"
    # poll uses the challenge, not the code.
    assert mock_poll.call_args.args[1] == "CHALLENGE456"
    # tailscale up uses the granted key/coord/hostname + --force-reauth.
    mock_run.assert_called_once_with(
        [
            "tailscale",
            "up",
            "--login-server=https://coord.example",
            "--authkey=tskey-abc123",
            "--hostname=my-box",
            "--force-reauth",
        ],
        timeout=TAILSCALE_UP_TIMEOUT_SECONDS,
    )


def test_join_defaults_name_to_hostname():
    runner = CliRunner()
    p_fetch, p_start, p_poll = _patch_flow()
    with p_fetch, p_start as mock_start, p_poll, patch(
        f"{MESH}.socket.gethostname", return_value="host42"
    ), patch(f"{MESH}.subprocess.run", return_value=_ok()):
        result = runner.invoke(
            cli, ["mesh", "join", "-u", "http://fakts.example", "--no-open-browser"]
        )

    assert result.exit_code == 0, result.output
    assert mock_start.call_args.args[1]["requested_machine_name"] == "host42"


def test_join_redacts_authkey_in_output():
    runner = CliRunner()
    p_fetch, p_start, p_poll = _patch_flow()
    with p_fetch, p_start, p_poll, patch(f"{MESH}.subprocess.run", return_value=_ok()):
        result = runner.invoke(
            cli, ["mesh", "join", "-u", "http://fakts.example", "--no-open-browser"]
        )

    assert result.exit_code == 0, result.output
    assert "--authkey=***" in result.output
    assert "tskey-abc123" not in result.output


def test_join_uses_hint_options_in_payload():
    runner = CliRunner()
    p_fetch, p_start, p_poll = _patch_flow()
    with p_fetch, p_start as mock_start, p_poll, patch(
        f"{MESH}.subprocess.run", return_value=_ok()
    ):
        result = runner.invoke(
            cli,
            [
                "mesh", "join", "-u", "http://fakts.example", "--no-open-browser",
                "--description", "gpu box", "--ephemeral",
                "--tag", "tag:a", "--tag", "tag:b", "--expiration", "120",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = mock_start.call_args.args[1]
    assert payload["description"] == "gpu box"
    assert payload["ephemeral"] is True
    assert payload["tags"] == ["tag:a", "tag:b"]
    assert payload["expiration_time_seconds"] == 120


def test_join_falls_back_to_wellknown_coord_when_poll_omits_it():
    runner = CliRunner()
    granted = {k: v for k, v in GRANTED.items() if k != "ionscale_coord_url"}
    p_fetch, p_start, p_poll = _patch_flow(granted=granted)
    with p_fetch, p_start, p_poll, patch(
        f"{MESH}.subprocess.run", return_value=_ok()
    ) as mock_run:
        result = runner.invoke(
            cli, ["mesh", "join", "-u", "http://fakts.example", "--no-open-browser"]
        )

    assert result.exit_code == 0, result.output
    assert "--login-server=https://coord.example" in mock_run.call_args.args[0]


def test_join_errors_when_deployment_lacks_mesh_endpoints():
    runner = CliRunner()
    with patch(f"{MESH}._fetch_well_known", return_value={"name": "F"}), patch(
        f"{MESH}.subprocess.run"
    ) as mock_run:
        result = runner.invoke(cli, ["mesh", "join", "-u", "http://fakts.example"])

    assert result.exit_code != 0
    # "device-code" is a single token, so rich line-wrapping can't split it.
    assert "device-code" in result.output
    mock_run.assert_not_called()


def test_join_not_installed_guides_install():
    runner = CliRunner()
    with patch(f"{MESH}.shutil.which", return_value=None), patch(
        f"{MESH}._fetch_well_known"
    ) as mock_fetch, patch(f"{MESH}.subprocess.run") as mock_run:
        result = runner.invoke(cli, ["mesh", "join", "-u", "http://fakts.example"])

    assert result.exit_code != 0
    assert "tailscale.com/download" in result.output
    # Fails fast: no network lookup and no tailscale invocation.
    mock_fetch.assert_not_called()
    mock_run.assert_not_called()


def test_cert_self_fqdn():
    runner = CliRunner()
    with patch(f"{MESH}.subprocess.run", return_value=_ok()) as mock_run:
        result = runner.invoke(cli, ["mesh", "cert"])

    assert result.exit_code == 0, result.output
    mock_run.assert_called_once_with(["tailscale", "cert"], timeout=TAILSCALE_UP_TIMEOUT_SECONDS)


def test_cert_explicit_domain():
    runner = CliRunner()
    with patch(f"{MESH}.subprocess.run", return_value=_ok()) as mock_run:
        result = runner.invoke(cli, ["mesh", "cert", "host.ts.net"])

    assert result.exit_code == 0, result.output
    mock_run.assert_called_once_with(
        ["tailscale", "cert", "host.ts.net"], timeout=TAILSCALE_UP_TIMEOUT_SECONDS
    )


def test_cert_not_installed_guides_install():
    runner = CliRunner()
    with patch(f"{MESH}.shutil.which", return_value=None), patch(
        f"{MESH}.subprocess.run"
    ) as mock_run:
        result = runner.invoke(cli, ["mesh", "cert"])

    assert result.exit_code != 0
    assert "tailscale.com/download" in result.output
    mock_run.assert_not_called()


def test_tailscale_sudo_fallback_on_nonzero_exit():
    runner = CliRunner()
    with patch(
        f"{MESH}.subprocess.run", side_effect=[_ok(1), _ok(0)]
    ) as mock_run:
        result = runner.invoke(cli, ["mesh", "cert"])

    assert result.exit_code == 0, result.output
    assert mock_run.call_count == 2
    assert mock_run.call_args_list[0].args[0] == ["tailscale", "cert"]
    assert mock_run.call_args_list[1].args[0] == ["sudo", "tailscale", "cert"]


def test_tailscale_binary_missing_at_runtime():
    runner = CliRunner()
    with patch(f"{MESH}.subprocess.run", side_effect=FileNotFoundError()):
        result = runner.invoke(cli, ["mesh", "cert"])

    assert result.exit_code != 0
    assert "tailscale" in result.output


# --------------------------------------------------------------------------
# leave
# --------------------------------------------------------------------------


def test_leave_yes_runs_logout():
    runner = CliRunner()
    with patch(f"{MESH}.subprocess.run", return_value=_ok()) as mock_run:
        result = runner.invoke(cli, ["mesh", "leave", "--yes"])

    assert result.exit_code == 0, result.output
    mock_run.assert_called_once_with(["tailscale", "logout"], timeout=TAILSCALE_UP_TIMEOUT_SECONDS)


def test_leave_without_yes_aborts_on_no():
    runner = CliRunner()
    with patch(f"{MESH}.subprocess.run") as mock_run:
        result = runner.invoke(cli, ["mesh", "leave"], input="n\n")

    assert result.exit_code != 0  # aborted
    mock_run.assert_not_called()


def test_leave_not_installed_guides_install():
    runner = CliRunner()
    with patch(f"{MESH}.shutil.which", return_value=None), patch(
        f"{MESH}.subprocess.run"
    ) as mock_run:
        result = runner.invoke(cli, ["mesh", "leave", "--yes"])

    assert result.exit_code != 0
    assert "tailscale.com/download" in result.output
    mock_run.assert_not_called()


# --------------------------------------------------------------------------
# proxy
# --------------------------------------------------------------------------


class _FakeProc:
    """A fake tailscaled process: wait() returns immediately, terminate() no-ops."""

    def __init__(self):
        self.terminated = False

    def wait(self, timeout=None):
        return 0

    def terminate(self):
        self.terminated = True

    def kill(self):
        pass


@pytest.fixture
def _tailscaled_found():
    with patch(f"{MESH}._find_tailscaled", return_value="/usr/sbin/tailscaled"):
        yield


def test_proxy_starts_daemon_and_brings_up(_tailscaled_found):
    runner = CliRunner()
    p_fetch, p_start, p_poll = _patch_flow()
    fake_proc = _FakeProc()
    with p_fetch, p_start, p_poll, patch(
        f"{MESH}.subprocess.Popen", return_value=fake_proc
    ) as mock_popen, patch(
        f"{MESH}.subprocess.run", return_value=_ok()
    ) as mock_run, patch(f"{MESH}.time.sleep"):
        result = runner.invoke(
            cli, ["mesh", "proxy", "-u", "http://fakts.example", "--no-open-browser"]
        )

    assert result.exit_code == 0, result.output
    # Userspace daemon command.
    daemon_cmd = mock_popen.call_args.args[0]
    assert daemon_cmd[0] == "/usr/sbin/tailscaled"
    assert "--tun=userspace-networking" in daemon_cmd
    assert "--outbound-http-proxy-listen=localhost:1055" in daemon_cmd
    assert any(a.startswith("--socket=") for a in daemon_cmd)
    assert not any(a.startswith("--socks5-server=") for a in daemon_cmd)
    # Bring-up via the daemon socket, with the granted key/coord/hostname.
    up_cmd = mock_run.call_args.args[0]
    assert up_cmd[0] == "tailscale"
    assert any(a.startswith("--socket=") for a in up_cmd)
    assert "up" in up_cmd
    assert "--login-server=https://coord.example" in up_cmd
    assert "--authkey=tskey-abc123" in up_cmd
    assert "--hostname=my-box" in up_cmd
    assert "--force-reauth" in up_cmd
    # Proxy URL is surfaced; the key is redacted in output.
    assert "http://localhost:1055" in result.output
    assert "tskey-abc123" not in result.output
    assert fake_proc.terminated


def test_proxy_socks5_listen_adds_flag(_tailscaled_found):
    runner = CliRunner()
    p_fetch, p_start, p_poll = _patch_flow()
    with p_fetch, p_start, p_poll, patch(
        f"{MESH}.subprocess.Popen", return_value=_FakeProc()
    ) as mock_popen, patch(f"{MESH}.subprocess.run", return_value=_ok()), patch(
        f"{MESH}.time.sleep"
    ):
        result = runner.invoke(
            cli,
            [
                "mesh", "proxy", "-u", "http://fakts.example", "--no-open-browser",
                "--socks5-listen", "localhost:1080",
            ],
        )

    assert result.exit_code == 0, result.output
    daemon_cmd = mock_popen.call_args.args[0]
    assert "--socks5-server=localhost:1080" in daemon_cmd


def test_proxy_custom_listen(_tailscaled_found):
    runner = CliRunner()
    p_fetch, p_start, p_poll = _patch_flow()
    with p_fetch, p_start, p_poll, patch(
        f"{MESH}.subprocess.Popen", return_value=_FakeProc()
    ) as mock_popen, patch(f"{MESH}.subprocess.run", return_value=_ok()), patch(
        f"{MESH}.time.sleep"
    ):
        result = runner.invoke(
            cli,
            [
                "mesh", "proxy", "-u", "http://fakts.example", "--no-open-browser",
                "--listen", "0.0.0.0:8080",
            ],
        )

    assert result.exit_code == 0, result.output
    daemon_cmd = mock_popen.call_args.args[0]
    assert "--outbound-http-proxy-listen=0.0.0.0:8080" in daemon_cmd
    assert "http://0.0.0.0:8080" in result.output


def test_proxy_tailscaled_missing_guides_install():
    runner = CliRunner()
    with patch(f"{MESH}._find_tailscaled", return_value=None), patch(
        f"{MESH}._fetch_well_known"
    ) as mock_fetch, patch(f"{MESH}.subprocess.Popen") as mock_popen:
        result = runner.invoke(
            cli, ["mesh", "proxy", "-u", "http://fakts.example", "--no-open-browser"]
        )

    assert result.exit_code != 0
    assert "tailscaled" in result.output
    # Fails fast: no join, no daemon.
    mock_fetch.assert_not_called()
    mock_popen.assert_not_called()


def test_proxy_bringup_failure_raises(_tailscaled_found):
    runner = CliRunner()
    p_fetch, p_start, p_poll = _patch_flow()
    fake_proc = _FakeProc()
    with p_fetch, p_start, p_poll, patch(
        f"{MESH}.subprocess.Popen", return_value=fake_proc
    ), patch(f"{MESH}.subprocess.run", return_value=_ok(1)), patch(
        f"{MESH}.time.sleep"
    ):
        result = runner.invoke(
            cli, ["mesh", "proxy", "-u", "http://fakts.example", "--no-open-browser"]
        )

    assert result.exit_code != 0
    # The daemon is still cleaned up on failure.
    assert fake_proc.terminated


# --------------------------------------------------------------------------
# stall bounds: poll deadline + tailscale subprocess timeout
# --------------------------------------------------------------------------


class _FakeResp:
    """Minimal aiohttp response context manager returning a fixed payload."""

    status = 200

    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def json(self, content_type=None):
        return self._payload

    async def text(self):
        return ""


class _FakeSession:
    """Minimal aiohttp ClientSession that always answers ``post`` with ``payload``."""

    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def post(self, url, json=None, timeout=None):
        return _FakeResp(self._payload)


def test_mesh_poll_times_out_when_never_authorized(capsys):
    """`_mesh_poll` raises (does not spin forever) once its deadline passes."""
    import itertools

    from arkitekt.cli.commands.mesh.main import _mesh_poll

    # A monotonic (ever-increasing) clock: safe for asyncio's own monotonic()
    # calls, and each step (100s) dwarfs the 1s timeout so the first 'pending'
    # check bails immediately -- deterministic, no real waiting.
    clock = itertools.count(0.0, 100.0)
    with patch(f"{MESH}.time.monotonic", side_effect=lambda: next(clock)), patch(
        "aiohttp.ClientSession", return_value=_FakeSession({"status": "pending"})
    ):
        # cli_error prints to stderr, then raises typer.Exit(1).
        with pytest.raises(typer.Exit):
            asyncio.run(_mesh_poll("http://fakts.example/challenge", "CH", timeout=1))

    assert "not authorized within" in capsys.readouterr().err


def test_tailscale_up_timeout_surfaces_clean_error():
    """A wedged `tailscale up` is aborted and reported, not left to hang."""
    runner = CliRunner()
    with patch(
        f"{MESH}.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="tailscale", timeout=TAILSCALE_UP_TIMEOUT_SECONDS),
    ):
        result = runner.invoke(cli, ["mesh", "cert"])

    assert result.exit_code != 0
    assert "did not finish within" in result.output
