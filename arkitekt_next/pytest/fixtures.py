"""Pytest fixtures for testing against a real Arkitekt server.

This module ships as a pytest plugin (see ``[project.entry-points.pytest11]`` in
``pyproject.toml``), so **every project that installs ``arkitekt-next`` gets these
fixtures automatically** -- no conftest wiring required::

    def test_my_app(running_app):
        result = running_app.app.rekuest.run(...)

Each fixture spins up a throwaway deployment with ``dokker``: a temporary config
with anonymous volumes and free ports, brought up, health-checked, and torn down
(volumes included) afterwards. Nothing is left on disk or in docker.

The fixtures are session-scoped because booting a stack costs image pulls plus
django migrations; ``arkitekt_server`` is a *factory*, so a test that needs a
different service selection can build its own without paying for a second copy of
the shared one.

Docker is required. Tests using these fixtures are skipped automatically when no
docker daemon is reachable, and are additionally marked ``integration`` so they
only run when explicitly selected with ``-m integration``.
"""

from __future__ import annotations

import shutil
import subprocess
from contextlib import ExitStack
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generator, List, Optional, cast

import pytest

if TYPE_CHECKING:
    from dokker import LogWatcher

    from arkitekt_next.app import App
    from arkitekt_next.server.dev import ArkitektServer, Channel

#: Services a general-purpose integration stack needs. ``lok`` is always enabled
#: (see ``dev.REQUIRED_SERVICES``) and provides auth.
DEFAULT_SERVICES = ["rekuest", "mikro", "kabinet"]

#: lok auto-configures a local hub with this identifier from the default kommunity
#: partners the generator writes into every config. ``validatecode`` resolves the
#: device code against it.
HUB_IDENTIFIER = "localhost"

#: Release channel for the service images. ``next`` tracks the development images
#: the current client is written against.
DEFAULT_CHANNEL = "next"


def docker_available() -> bool:
    """Return True if a docker CLI and a reachable daemon are present."""
    if shutil.which("docker") is None:
        return False
    try:
        return (
            subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            ).returncode
            == 0
        )
    except Exception:
        return False


def pytest_configure(config: pytest.Config) -> None:
    """Register the markers this plugin applies, so downstream projects don't warn."""
    config.addinivalue_line(
        "markers",
        "integration: test needs a running Arkitekt server (run with -m integration)",
    )
    config.addinivalue_line(
        "markers", "needs_docker: test needs a reachable docker daemon"
    )


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register this plugin's command line options."""
    parser.addoption(
        "--arkitekt-channel",
        action="store",
        default=DEFAULT_CHANNEL,
        help=(
            "Release channel for the Arkitekt service images spun up by the "
            f"test fixtures ('next' or 'latest'). Defaults to {DEFAULT_CHANNEL!r}."
        ),
    )


def _require_docker() -> None:
    """Skip the calling test when docker is unavailable."""
    if not docker_available():
        pytest.skip("requires a reachable docker daemon")


@dataclass
class AppWithinDeployment:
    """A running Arkitekt server together with an app connected to it."""

    server: "ArkitektServer"
    app: "App"

    def watch(self, *services: str) -> "LogWatcher":
        """Capture container logs for the duration of a ``with`` block.

        On failure inside the block, dokker appends the captured logs to the
        traceback -- usually the difference between "the request 500ed" and knowing
        why::

            with running_app.watch("mikro"):
                assert upload_something()

        Passing no service names watches every deployed service.
        """
        return self.server.watch(*services)


#: Factory signature returned by the ``arkitekt_server`` fixture.
ArkitektServerFactory = Callable[..., "ArkitektServer"]


@pytest.fixture(scope="session")
def arkitekt_channel(request: pytest.FixtureRequest) -> str:
    """Release channel used for the service images."""
    return str(request.config.getoption("--arkitekt-channel"))


@pytest.fixture(scope="session")
def arkitekt_server(
    arkitekt_channel: str,
) -> Generator[ArkitektServerFactory, None, None]:
    """Factory that boots throwaway Arkitekt deployments.

    Call it to get a running, health-checked server::

        def test_something(arkitekt_server):
            server = arkitekt_server(["rekuest", "mikro"])
            assert server.gateway_url

        def test_coordinator_only(arkitekt_server):
            coord = arkitekt_server(kind="coord")

    Every deployment created through the factory is torn down when the session
    ends. Calling it more than once yields independent stacks -- dokker gives each
    a unique compose project name and the config picks free ports, so they do not
    collide.
    """
    from arkitekt_next.server.dev import temp_setup

    _require_docker()
    stack = ExitStack()

    def factory(
        services: Optional[List[str]] = None,
        *,
        kind: str = "hubinator",
        config=None,
        channel: Optional[str] = None,
        pull: bool = True,
    ) -> "ArkitektServer":
        server = stack.enter_context(
            temp_setup(
                services,
                kind=kind,
                config=config,
                # The channel is a CLI-provided string; ``temp_setup`` types it as a
                # Literal, and validates it downstream.
                channel=cast("Channel", channel or arkitekt_channel),
            )
        )
        setup = stack.enter_context(server.setup)
        if pull:
            setup.pull()
        setup.up()
        setup.check_health()
        return server

    try:
        yield factory
    finally:
        # Unwinds every deployment: the `testing` teardown policy downs each stack
        # and removes its volumes and orphans.
        stack.close()


@pytest.fixture(scope="session")
def running_server(arkitekt_server: ArkitektServerFactory) -> "ArkitektServer":
    """A running full Arkitekt stack with the default services."""
    return arkitekt_server(DEFAULT_SERVICES)


@pytest.fixture(scope="session")
def lok_server(arkitekt_server: ArkitektServerFactory) -> "ArkitektServer":
    """A running lok-only stack (gateway + lok + infrastructure).

    Much faster to boot than the full stack -- use it for tests that only talk to
    the coordination server. Drive lok through ``lok_server.lok`` to approve device
    codes, authorize hubs, or run management commands.
    """
    return arkitekt_server([])


@pytest.fixture(scope="session")
def running_app(
    running_server: "ArkitektServer",
) -> Generator[AppWithinDeployment, None, None]:
    """An ``easy`` app connected to a running Arkitekt server.

    The device-code login is approved server-side through the lok controller, which
    runs lok's ``validatecode`` management command inside the container -- so the
    test never has to open a browser.
    """
    from fakts_next.grants.remote import FaktsEndpoint

    from arkitekt_next import easy
    from arkitekt_next.service_registry import get_default_service_registry

    async def device_code_hook(endpoint: FaktsEndpoint, device_code: str) -> None:
        await running_server.lok.avalidate_device_code(device_code, hub=HUB_IDENTIFIER)

    registry = get_default_service_registry()
    assert registry, "Service registry must be initialized"

    with easy(
        url=running_server.gateway_url,
        device_code_hook=device_code_hook,
    ) as app:
        yield AppWithinDeployment(server=running_server, app=app)
