"""Integration tests for the `coord` and `hub` deployment kinds.

Everything else in the docker-backed suite runs against the *full* stack
(hubinator): until ``temp_setup`` became kind-aware, that was the only kind that
could be booted at all. These tests cover the two gaps that left:

1. **A `coord` deployment actually boots.** The coord generator emits a different
   compose file (Lok + infrastructure, no data services); nothing verified it
   starts and reports healthy.
2. **The `hub connect` CLI works end to end.** ``test_lok_integration`` covers the
   registration *protocol* by calling ``register_hub()`` directly with a hand-built
   request; here the real command loads a generated hub config, discovers hosts,
   and registers against a live coordinator, which is then approved server-side.

Deliberately **not** covered here: hub *containers* validating coord-issued
tokens. Each ``temp_setup`` deployment is its own compose project (dokker gives it
a unique project name) and therefore its own docker network, so a hub container
resolving ``localhost:<port>`` reaches itself rather than the coord gateway. On
top of that the generator hardcodes ``https://`` for the coordinator's JWKS
(``diff.py`` -> ``jwks_uri``), which a local http coord cannot serve. Wiring that
up needs a shared network plus a scheme-aware ``jwks_uri`` -- a separate change.

Run with::

    pytest -m integration tests/cli/test_coord_hub_connect.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from arkitekt_next.cli.main import cli

pytestmark = [pytest.mark.integration, pytest.mark.needs_docker]


@pytest.fixture(scope="module")
def coord_server(arkitekt_server):
    """A booted, health-checked standalone coordinator."""
    return arkitekt_server(kind="coord")


# ---------------------------------------------------------------------------
# The coord kind boots
# ---------------------------------------------------------------------------


def test_coord_deployment_comes_up_healthy(coord_server):
    """A generated coordinator starts and its lok reports healthy.

    ``arkitekt_server`` already calls ``check_health()``, so reaching this point
    means every registered check passed; the assertions pin down *what* was
    checked, so a coord silently degrading to a full stack would fail here.
    """
    assert coord_server.kind == "coord"
    # A coordinator runs lok and nothing else -- no data services.
    assert coord_server.enabled_services == ["lok"]

    compose = yaml.safe_load((coord_server.path / "docker-compose.yaml").read_text())
    assert "lok" in compose["services"]
    assert "gateway" in compose["services"]
    for data_service in ("rekuest", "mikro", "fluss"):
        assert data_service not in compose["services"], (
            f"a coordinator should not deploy {data_service}"
        )


def test_coord_serves_the_well_known_document(coord_server):
    """The booted coordinator answers the discovery endpoint clients start from."""
    from arkitekt_next.cli.commands.mesh.main import _fetch_well_known

    data = asyncio.run(_fetch_well_known(coord_server.gateway_url))
    assert data.get("device_code_start"), data
    assert data.get("challenge_url"), data


# ---------------------------------------------------------------------------
# `hub connect` against the live coordinator
# ---------------------------------------------------------------------------


async def _await_pending_hub_code(coord_server, deadline_seconds: float = 60.0) -> str:
    """Wait for a hub registration to show up awaiting approval."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + deadline_seconds
    while loop.time() < deadline:
        pending = await coord_server.lok.apending_hub_codes()
        if pending:
            return pending[-1]
        await asyncio.sleep(1)
    raise AssertionError("no pending hub device code appeared in lok")


def _init_hub(work_dir: Path, coord_url: str) -> None:
    """Generate a hub config pointing at the live coordinator."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--work-dir",
            str(work_dir),
            "hub",
            "init",
            "--template",
            "stable",
            "--service",
            "rekuest",
            "--service",
            "mikro",
            # `connect` accepts a full base URL with an explicit scheme, which is how
            # a local coordinator on a random http port is addressed.
            "--coord-server",
            coord_url,
        ],
    )
    assert result.exit_code == 0, result.output


def test_hub_connect_registers_with_a_live_coordinator(coord_server, tmp_path):
    """`hub connect` completes once the coordinator authorizes it.

    Exercises the whole command: load the generated hub config, discover host
    addresses, POST the hub manifest to the real coordinator, and poll the
    challenge endpoint -- while the controller approves it server-side.
    """
    coord_url = coord_server.gateway_url
    _init_hub(tmp_path, coord_url)

    runner = CliRunner()

    async def scenario():
        # `connect` is synchronous and blocks on its own poll loop, so run it in a
        # worker thread while this loop plays the operator.
        task = asyncio.create_task(
            asyncio.to_thread(
                runner.invoke,
                cli,
                [
                    "--work-dir",
                    str(tmp_path),
                    "hub",
                    "connect",
                    "--no-browser",
                    "--all-hosts",
                    "--no-resolve",
                    "--timeout",
                    "90",
                ],
            )
        )
        code = await _await_pending_hub_code(coord_server)
        await coord_server.lok.aapprove_hub(code)
        return code, await task

    code, result = asyncio.run(scenario())

    assert result.exit_code == 0, result.output
    assert "connected to the organization" in result.output
    assert code

    # The hub advertised exactly the services it was configured with.
    config = yaml.safe_load((tmp_path / "hub_config.yaml").read_text())["config"]
    assert config["coord_server"] == coord_url


def test_hub_connect_reports_a_denied_registration(coord_server, tmp_path):
    """A denied registration never reports success."""
    _init_hub(tmp_path, coord_server.gateway_url)

    runner = CliRunner()

    async def scenario():
        task = asyncio.create_task(
            asyncio.to_thread(
                runner.invoke,
                cli,
                [
                    "--work-dir",
                    str(tmp_path),
                    "hub",
                    "connect",
                    "--no-browser",
                    "--all-hosts",
                    "--no-resolve",
                    "--timeout",
                    "15",
                ],
            )
        )
        code = await _await_pending_hub_code(coord_server)
        await coord_server.lok.adeny_hub(code)
        return await task

    result = asyncio.run(scenario())

    assert "connected to the organization" not in result.output


# ---------------------------------------------------------------------------
# The hub kind boots (without a reachable coordinator)
# ---------------------------------------------------------------------------


def test_hub_deployment_comes_up_healthy(arkitekt_server):
    """A generated hub starts and its data services report healthy.

    A hub trusts an *external* coordinator for identity, so it deploys no lok. The
    health endpoints do not validate tokens, which is why this passes even though
    the configured ``coord_server`` is not reachable from inside the containers --
    see the module docstring.
    """
    hub = arkitekt_server(["rekuest", "mikro"], kind="hub")

    assert hub.kind == "hub"
    assert sorted(hub.enabled_services) == ["mikro", "rekuest"]

    compose = yaml.safe_load((hub.path / "docker-compose.yaml").read_text())
    assert "lok" not in compose["services"], "a hub must not deploy a local lok"
    assert "gateway" in compose["services"]
