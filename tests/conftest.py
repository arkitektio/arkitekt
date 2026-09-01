"""Test configuration for arkitekt-next itself.

The docker-backed fixtures (``arkitekt_server``, ``lok_server``, ``running_app``)
are **not** defined here: they ship in :mod:`arkitekt_next.pytest`, which pytest
auto-loads via the ``pytest11`` entry point. Using them from this repo's own suite
is deliberate -- it means the plugin our users get is the plugin we test.

What stays here is repo-local: CLI runner fixtures and the marker gating.
"""

from __future__ import annotations

import pytest
from arkitekt_next.cli.main import cli
from arkitekt_next.pytest.fixtures import AppWithinDeployment, docker_available
from click.testing import CliRunner

# Re-exported so tests can `from .conftest import AppWithinDeployment`.
__all__ = ["AppWithinDeployment"]


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Gate tests that need external services.

    Every test runs by default, except:
    - ``integration`` tests (which require a running arkitekt-server) — skipped
      unless explicitly selected with ``-m integration``;
    - ``needs_docker`` tests — skipped when no docker daemon is reachable, so
      they no-op on macOS/Windows CI runners and dev machines without docker.

    Docker-backed stack tests carry **both** markers: opt-in via ``-m integration``
    so a bare ``pytest`` stays fast, and a clean skip when there is no daemon.
    """
    docker_ok = docker_available()
    # `-m integration` selects integration tests; only then do we run them.
    run_integration = "integration" in str(config.getoption("markexpr") or "")
    skip_no_docker = pytest.mark.skip(reason="docker daemon not available")
    skip_integration = pytest.mark.skip(
        reason="integration tests require a running arkitekt-server; run with -m integration"
    )
    for item in items:
        # Use get_closest_marker (not `in item.keywords`): keywords also contain
        # path-derived names like the `cli` directory, which would over-match.
        if item.get_closest_marker("integration") is not None and not run_integration:
            item.add_marker(skip_integration)
        if item.get_closest_marker("needs_docker") is not None and not docker_ok:
            item.add_marker(skip_no_docker)


@pytest.fixture(autouse=True)
def _assume_interactive(monkeypatch):
    """Make the CLI treat itself as interactive during tests.

    ``CliRunner`` replaces ``sys.stdin`` with a non-TTY stream, so the
    ``require_interactive`` guard (added to every prompt site) would abort any
    test that drives a prompt via ``input=``. Tests that specifically exercise
    the non-TTY guard patch ``is_interactive`` back to ``False`` themselves.
    """
    monkeypatch.setattr(
        "arkitekt_next.cli.interactive.is_interactive", lambda: True
    )



@pytest.fixture
def initialized_app_cli_runner():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "app",
                "init",
                "--identifier",
                "arkitekt-next",
                "--version",
                "0.0.1",
                "--author",
                "arkitek",
                "--template",
                "simple",
                "--scopes",
                "read",
                "--scopes",
                "write",
            ],
        )
        assert result.exit_code == 0, result.output
        yield runner


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def app_dir(tmp_path):
    """Temp dir with an initialized app, using --work-dir (no os.chdir)."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--work-dir",
            str(tmp_path),
            "app",
            "init",
            "--identifier",
            "com.test.app",
            "--version",
            "0.0.1",
            "--author",
            "tester",
            "--entrypoint",
            "app",
            "--package-manager",
            "pip",
        ],
    )
    assert result.exit_code == 0, result.output
    return tmp_path


@pytest.fixture
def app_runner(app_dir):
    """CliRunner paired with a pre-initialized app directory."""
    runner = CliRunner()
    return runner, app_dir
