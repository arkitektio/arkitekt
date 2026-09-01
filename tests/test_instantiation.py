"""Tests that ``easy()`` produces a usable app against a real server.

This used to call ``easy("johannes", "latest")`` with no fixture and no server, so
under ``-m integration`` it could only hang or fail. It now uses the ``running_app``
fixture, which connects an app to a throwaway deployment and approves the
device-code login server-side.
"""

import pytest

from arkitekt_next.pytest.fixtures import AppWithinDeployment


@pytest.mark.integration
@pytest.mark.needs_docker
def test_easy_connects_to_a_running_server(running_app: AppWithinDeployment) -> None:
    """``easy`` negotiates a config and builds the registered services."""
    app = running_app.app

    assert app.manifest is not None, "The app should carry its manifest"
    assert app.fakts is not None, "fakts should have negotiated against the server"
    assert app.services, "The app should have built at least one service"


@pytest.mark.integration
@pytest.mark.needs_docker
def test_app_services_match_the_deployed_services(
    running_app: AppWithinDeployment,
) -> None:
    """The services the app built should exist on the deployment it connected to."""
    deployed = set(running_app.server.enabled_services)

    # `lok` is always deployed and is what the app authenticated against.
    assert "lok" in deployed
    # Every service the app built should be one the server actually runs.
    assert set(running_app.app.services) & deployed, (
        f"App built {sorted(running_app.app.services)}, "
        f"deployment runs {sorted(deployed)}"
    )
