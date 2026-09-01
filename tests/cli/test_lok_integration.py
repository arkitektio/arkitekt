"""CLI <-> lok integration tests against a real, fully controlled lok server.

These run the CLI's *actual* network stack (well-known discovery, device-code
auth, hub registration) against a real dockerized lok deployment --
the session-scoped, lok-only ``lok_server`` fixture -- and play the human
operator server-side through ``lok_server.lok`` (the :class:`LokController`):
approving device codes, authorizing or denying hub registrations.

They double as *contract tests*: whenever lok's endpoints change shape, these
fail here first, before any mocked unit test drifts out of sync.

Run with::

    pytest -m integration tests/cli/test_lok_integration.py
"""

from __future__ import annotations

import asyncio

import click
import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Well-known contract
# ---------------------------------------------------------------------------


def test_well_known_serves_the_keys_the_cli_relies_on(lok_server):
    """The `/.well-known/fakts` document advertises the fakts endpoints.

    ``_fetch_well_known`` is the CLI's own fetcher (mesh commands), and the
    asserted keys are the ones the device-code auth stack (``fakts_next``)
    resolves before any flow can start.
    """
    from arkitekt_next.cli.commands.mesh.main import _fetch_well_known

    data = asyncio.run(_fetch_well_known(lok_server.gateway_url))

    for key in (
        "name",
        "version",
        "base_url",
        "protocol_version",
        "issuer",
        "token_endpoint",
        "device_authorization_endpoint",
    ):
        assert data.get(key), f"well-known document is missing {key!r}: {data}"

    assert data["protocol_version"] == "2", (
        f"expected fakts protocol v2, got {data['protocol_version']!r}"
    )

    # The advertised endpoints must be absolute URLs. Deployments sit behind a
    # script-name prefix, so a client that reconstructs them by concatenating
    # onto the issuer gets the path wrong.
    for key in ("token_endpoint", "device_authorization_endpoint"):
        assert data[key].startswith("http"), f"{key!r} is not absolute: {data[key]}"

    # The v1 endpoints are gone; asserting their absence keeps a half-migrated
    # server from looking healthy.
    for legacy in ("claim", "device_code_start", "challenge_url", "token_url"):
        assert legacy not in data, f"{legacy!r} is a protocol v1 endpoint: {data}"


# ---------------------------------------------------------------------------
# App device-code login (the auth stack behind `app run dev`)
# ---------------------------------------------------------------------------


def test_device_code_login_negotiates_config(lok_server, tmp_path, monkeypatch):
    """The CLI's device-code auth stack completes against a real lok.

    Uses ``build_device_code_fakts`` -- exactly what the ``easy`` builder wires
    up for `app run dev` -- headless, with the approval driven server-side via
    the lok controller instead of a human in the browser.
    """
    from arkitekt_next.app.fakts import build_device_code_fakts
    from fakts_next.models import Manifest

    # The fakts FileCache writes .arkitekt_next/cache/ relative to the CWD.
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".arkitekt_next" / "cache").mkdir(parents=True)

    manifest = Manifest(
        identifier="com.example.lok-integration",
        version="0.0.1",
        scopes=["read"],
    )

    approved: list[str] = []

    async def device_code_hook(endpoint, device_code: str) -> None:
        await lok_server.lok.avalidate_device_code(device_code)
        approved.append(device_code)

    fakts = build_device_code_fakts(
        manifest,
        url=lok_server.gateway_url,
        headless=True,
        device_code_hook=device_code_hook,
    )

    async def negotiate():
        async with fakts:
            return await fakts.aload()

    active = asyncio.run(negotiate())

    assert approved, "the device-code hook was never invoked"
    assert active.self, "negotiation returned no self fakt"
    assert active.auth, "negotiation returned no auth fakt"


# ---------------------------------------------------------------------------
# Hub registration (the flow behind `hub connect`)
# ---------------------------------------------------------------------------


def _hub_request(identifier: str):
    """A minimal hub registration, shaped like ``build_hub``'s output."""
    from arkitekt_next.server.connect import (
        HubManifest,
        HubStartRequest,
        InstanceConfigure,
        ServiceManifest,
        StagingAlias,
    )

    return HubStartRequest(
        hub=HubManifest(
            identifier=identifier,
            instances=[
                InstanceConfigure(
                    identifier="rekuest",
                    manifest=ServiceManifest(
                        identifier="live.arkitekt.rekuest",
                        name="Rekuest",
                        description="Integration-test instance",
                    ),
                    aliases=[
                        StagingAlias(
                            id="rekuest-0",
                            name="rekuest",
                            host="hub.example.org",
                            port=443,
                            path="rekuest",
                            ssl=True,
                        )
                    ],
                )
            ],
        )
    )


async def _await_pending_code(lok_server, deadline_seconds: float = 30.0) -> str:
    """Await a hub registration showing up awaiting approval (async, no thread)."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + deadline_seconds
    while loop.time() < deadline:
        pending = await lok_server.lok.apending_hub_codes()
        if pending:
            return pending[-1]
        await asyncio.sleep(1)
    raise AssertionError("no pending hub device code appeared in lok")


def test_hub_connect_completes_once_lok_authorizes(lok_server):
    """``register_hub`` (behind `hub connect`) completes end-to-end.

    The CLI's async poll of the real challenge endpoint runs concurrently with
    the lok controller playing the operator and authorizing the registration --
    both on one event loop, no threads.
    """
    from arkitekt_next.server.connect import register_hub

    request = _hub_request("integration-hub")

    async def scenario():
        task = asyncio.create_task(
            register_hub(
                request,
                server=lok_server.gateway_url,
                open_browser=False,
                timeout=60,
                poll_interval=1.0,
            )
        )
        code = await _await_pending_code(lok_server)
        await lok_server.lok.aapprove_hub(code)
        completed, configure_url = await task
        return code, completed, configure_url

    code, completed, configure_url = asyncio.run(scenario())

    assert completed is True
    assert configure_url.endswith(code)


def test_hub_connect_does_not_complete_when_lok_denies(lok_server):
    """A denied registration never reports completion (the CLI times out)."""
    from arkitekt_next.server.connect import register_hub

    request = _hub_request("integration-hub-denied")

    async def scenario():
        task = asyncio.create_task(
            register_hub(
                request,
                server=lok_server.gateway_url,
                open_browser=False,
                timeout=6,
                poll_interval=1.0,
            )
        )
        code = await _await_pending_code(lok_server)
        await lok_server.lok.adeny_hub(code)
        completed, _configure_url = await task
        return completed

    completed = asyncio.run(scenario())

    assert completed is False


# ---------------------------------------------------------------------------
# Mesh join (the mesh device-code flow behind `mesh join`)
# ---------------------------------------------------------------------------
#
# The granted path is not exercised here: a granted mesh join requires a minted
# ionscale pre-auth key (the lok-only stack advertises no ``mesh_coord_url`` and
# runs no ionscale coordinator) and would then shell out to ``tailscale up``.
# We instead cover everything up to authorization -- endpoint discovery, start,
# and both non-granted outcomes -- driving lok server-side via the controller.


async def _start_mesh_join(lok_server, *, expiration_time_seconds: int = 600):
    """Discover the mesh endpoints and start a join; returns ``(endpoints, code, challenge)``.

    Mirrors the payload ``mesh._device_code_join`` sends, so this exercises the
    same start endpoint the CLI hits.
    """
    from arkitekt_next.cli.commands.mesh.main import (
        _extract_mesh_endpoints,
        _fetch_well_known,
        _mesh_start,
    )

    data = await _fetch_well_known(lok_server.gateway_url)
    endpoints = _extract_mesh_endpoints(data, lok_server.gateway_url)
    payload = {
        "requested_machine_name": "integration-test",
        "description": "integration test",
        "ephemeral": False,
        "tags": [],
        "expiration_time_seconds": expiration_time_seconds,
    }
    code, challenge = await _mesh_start(str(endpoints["start_url"]), payload)
    return endpoints, code, challenge


def test_well_known_advertises_the_mesh_device_code_endpoints(lok_server):
    """Current lok ships the mesh device-code flow (start + challenge endpoints).

    ``_extract_mesh_endpoints`` raises when either is missing, so a clean return
    is the contract check.
    """
    from arkitekt_next.cli.commands.mesh.main import (
        _extract_mesh_endpoints,
        _fetch_well_known,
    )

    data = asyncio.run(_fetch_well_known(lok_server.gateway_url))
    endpoints = _extract_mesh_endpoints(data, lok_server.gateway_url)

    assert str(endpoints["start_url"]).endswith("/lok/f/meshstart/")
    assert str(endpoints["challenge_url"]).endswith("/lok/f/meshchallenge/")


def test_mesh_join_reports_denial_when_lok_denies(lok_server):
    """A denied mesh join surfaces the denial (mirrors the hub deny path).

    The CLI's real challenge poll runs against a join the lok controller denies
    server-side; the poll must raise rather than hang or report success.
    """
    from arkitekt_next.cli.commands.mesh.main import _mesh_poll

    async def scenario():
        endpoints, code, challenge = await _start_mesh_join(lok_server)
        await lok_server.lok.adeny_mesh(code)
        with pytest.raises(click.ClickException, match="denied by the authorizer"):
            await _mesh_poll(str(endpoints["challenge_url"]), challenge, timeout=30)

    asyncio.run(scenario())


def test_mesh_join_times_out_when_never_authorized(lok_server):
    """An unapproved mesh join times out client-side instead of hanging.

    The join stays pending (nobody authorizes it), so the CLI's own poll deadline
    must fire and raise a clear timeout error.
    """
    from arkitekt_next.cli.commands.mesh.main import _mesh_poll

    async def scenario():
        endpoints, _code, challenge = await _start_mesh_join(lok_server)
        with pytest.raises(click.ClickException, match="was not authorized within"):
            await _mesh_poll(str(endpoints["challenge_url"]), challenge, timeout=2)

    asyncio.run(scenario())
