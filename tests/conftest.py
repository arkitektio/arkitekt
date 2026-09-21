"""Test configuration for arkitekt itself.

Repo-local CLI runner fixtures and the marker gating. Server-backed fixtures are
gone along with the server-construction code: deployments are konstruktor's job
(https://github.com/arkitektio/konstruktor).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

import pytest
from arkitekt.cli.main import cli
from click.testing import CliRunner


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


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Gate tests that need external services.

    Every test runs by default, except ``needs_docker`` tests, which are skipped
    when no docker daemon is reachable, so they no-op on macOS/Windows CI runners
    and dev machines without docker.
    """
    docker_ok = docker_available()
    skip_no_docker = pytest.mark.skip(reason="docker daemon not available")
    for item in items:
        # Use get_closest_marker (not `in item.keywords`): keywords also contain
        # path-derived names like the `cli` directory, which would over-match.
        if item.get_closest_marker("needs_docker") is not None and not docker_ok:
            item.add_marker(skip_no_docker)


@pytest.fixture(autouse=True)
def _offline_fakts(monkeypatch):
    """Give every run a hot-pluggable fakts instead of a real one.

    A runtime builds its fakts from the manifest it is about to send; here that
    becomes a ``TestingFakts`` whose aliases answer every requirement the
    manifest lists, so services build their clients without a server.
    """
    from fakts.testing import build_testing_fakts

    def offline(manifest, options):  # noqa: ANN001, ANN202
        return build_testing_fakts(
            aliases={r.key: f"http://{r.key}.test" for r in manifest.requirements}
        )

    monkeypatch.setattr("arkitekt.runtime.build_fakts", offline)


@pytest.fixture(autouse=True)
def _assume_interactive(monkeypatch):
    """Make the CLI treat itself as interactive during tests.

    ``CliRunner`` replaces ``sys.stdin`` with a non-TTY stream, so the
    ``require_tty`` guard (added to every prompt site) would abort any
    test that drives a prompt via ``input=``. Tests that specifically exercise
    the non-TTY guard patch ``is_tty`` back to ``False`` themselves.
    """
    monkeypatch.setattr(
        "arkitekt.cli.tty.is_tty", lambda: True
    )


@pytest.fixture(autouse=True)
def _isolate_app_imports(monkeypatch):
    """Give every test its own ``sys.path`` and forget the app modules it imported.

    The CLI puts ``--work-dir`` on ``sys.path`` and imports the user's module from
    there. In one process across many tests, earlier work dirs would otherwise
    stay importable, and a test whose work dir has no ``app.py`` would silently
    get another test's.
    """
    monkeypatch.setattr(sys, "path", list(sys.path))
    before = set(sys.modules)
    yield
    scratch = os.path.realpath(tempfile.gettempdir())
    for name in set(sys.modules) - before:
        module_file = getattr(sys.modules.get(name), "__file__", None) or ""
        if os.path.realpath(module_file).startswith(scratch):
            sys.modules.pop(name, None)


def assert_only_the_entrypoint_was_scaffolded(work_dir, entrypoint: str = "app") -> None:
    """`init` writes the app's module and nothing else: the App in it is the identity."""
    import os

    assert os.path.exists(os.path.join(work_dir, f"{entrypoint}.py"))
    assert not os.path.exists(os.path.join(work_dir, ".arkitekt", "manifest.yaml"))


@pytest.fixture
def initialized_app_cli_runner():
    """A CliRunner inside an isolated filesystem that holds a scaffolded ``app.py``."""
    runner = CliRunner()
    with runner.isolated_filesystem() as work_dir:
        result = runner.invoke(
            cli,
            [
                "init",
                "--identifier",
                "arkitekt",
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
                "--package-manager",
                "pip",
            ],
        )
        assert result.exit_code == 0, result.output
        assert_only_the_entrypoint_was_scaffolded(work_dir)
        yield runner


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def app_dir(tmp_path):
    """Temp dir with a scaffolded ``app.py``, using --work-dir (no os.chdir).

    The app is ``App("com.test.app", "0.0.1", author="tester", scopes=["read"])``
    from the `simple` template.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--work-dir",
            str(tmp_path),
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
    assert_only_the_entrypoint_was_scaffolded(tmp_path)
    return tmp_path


@pytest.fixture
def app_runner(app_dir):
    """CliRunner paired with a directory holding a scaffolded app."""
    runner = CliRunner()
    return runner, app_dir
