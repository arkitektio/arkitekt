"""Docker-backed tests for the kabinet ``init`` -> ``build`` -> ``publish`` lifecycle.

These tests run a real ``docker build`` and therefore require a running docker
daemon. They are marked with ``needs_docker`` so they are skipped automatically
where docker is unavailable (see ``tests/conftest.py``).

The whole flow runs inside ``runner.isolated_filesystem()`` (which ``chdir``s into a
temp dir) rather than ``--work-dir``, because ``kabinet publish`` resolves its
builds/deployments against the current working directory.

Note on inspection: ``kabinet build`` (without ``--no-inspect``) runs the freshly
built container and executes ``arkitekt-next inspect all`` inside it. That command
belongs to the *released* ``arkitekt-next`` installed into the image from PyPI, which
is currently incompatible with this checkout (``AppRegistry`` has no
``state_registry``). We therefore stub only that one in-container call via
``_patched_inspect_all`` so the rest of the path stays real: ``docker build``,
``docker inspect`` (image size), the build-record bookkeeping, ``docker tag`` and the
deployment bookkeeping all run for real. ``docker push`` is stubbed in publish so the
tests need no registry/credentials.
"""

import subprocess
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from arkitekt_next.cli.main import cli
from arkitekt_next.cli.commands.plugin.io import get_builds, get_deployments


pytestmark = pytest.mark.needs_docker

# A minimal but schema-valid runtime payload, standing in for the result of running
# ``arkitekt-next inspect all`` inside the container (keys map to InspectionInput).
_FAKE_RUNTIME = {
    "locks": [],
    "implementations": [],
    "states": [],
    "requirements": [],
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _scaffold(runner: CliRunner, version: str = "0.0.1") -> None:
    """Create an app (`init`) and a vanilla flavour (`kabinet init`) in the CWD."""
    result = runner.invoke(
        cli,
        [
            "init",
            "--identifier", "com.test.app",
            "--version", version,
            "--author", "me",
            "--entrypoint", "app",
            "--package-manager", "pip",
        ],
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(
        cli,
        [
            "plugin", "init",
            "--flavour", "vanilla",
            "--arkitekt-version", "0.0.1",
        ],
        input="n\n",  # decline the devcontainer.json prompt
    )
    assert result.exit_code == 0, result.output


def _cleanup_images() -> None:
    """Best-effort removal of any images built by the current CWD's builds.yaml."""
    try:
        builds = get_builds()
    except Exception:
        return
    for build_id in builds:
        subprocess.run(
            ["docker", "rmi", "-f", build_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _patched_inspect_all():
    """Stub the (upstream-broken) in-container ``arkitekt-next inspect all`` call.

    The real ``docker inspect`` for image size still runs, so the build's inspection
    record carries a real size while the container-runtime payload is canned.
    """
    return patch(
        "arkitekt_next.cli.commands.plugin.build.inspect_all",
        return_value=_FAKE_RUNTIME,
    )


def _patched_push():
    """Patch only the ``docker push`` subprocess call, letting ``docker tag`` run."""
    real_run = subprocess.run

    def fake_run(cmd, *args, **kwargs):
        if isinstance(cmd, (list, tuple)) and list(cmd[:2]) == ["docker", "push"]:
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, *args, **kwargs)

    return patch(
        "arkitekt_next.cli.commands.plugin.publish.subprocess.run",
        side_effect=fake_run,
    )


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def test_kabinet_build_no_inspect():
    """`kabinet build --no-inspect` runs a real docker build and records it."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        _scaffold(runner)
        try:
            result = runner.invoke(cli, ["plugin", "build", "--no-inspect"])
            if result.exit_code != 0:
                print(result.output)
                print(result.exception)
            assert result.exit_code == 0

            builds = get_builds()
            assert len(builds) == 1
            (build_id, build), = builds.items()
            assert build.flavour == "vanilla"
            assert build.build_id == build_id
            assert build_id  # non-empty tag
            assert build.inspection is None  # inspection was skipped
        finally:
            _cleanup_images()


def test_kabinet_build_with_inspect():
    """`kabinet build` (default) builds the image and inspects it.

    Real ``docker build`` + real ``docker inspect`` (size); the in-container
    ``inspect all`` call is stubbed (see module docstring).
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        _scaffold(runner)
        try:
            with _patched_inspect_all():
                result = runner.invoke(cli, ["plugin", "build"])
            if result.exit_code != 0:
                print(result.output)
                print(result.exception)
            assert result.exit_code == 0

            builds = get_builds()
            assert len(builds) == 1
            (_, build), = builds.items()
            assert build.flavour == "vanilla"
            assert build.inspection is not None
            assert build.inspection.size is not None  # real `docker inspect` size
        finally:
            _cleanup_images()


# ---------------------------------------------------------------------------
# publish (init -> build -> publish, tag only)
# ---------------------------------------------------------------------------

def test_kabinet_full_lifecycle():
    """init -> kabinet init -> build -> publish: the full flow, push patched out."""
    tag = "localhost:5000/com.test.app:0.0.1-vanilla"
    runner = CliRunner()
    with runner.isolated_filesystem():
        _scaffold(runner)
        try:
            with _patched_inspect_all():
                result = runner.invoke(cli, ["plugin", "build"])
            assert result.exit_code == 0, result.output

            with _patched_push():
                result = runner.invoke(cli, ["plugin", "publish", "--tag", tag])
            if result.exit_code != 0:
                print(result.output)
                print(result.exception)
            assert result.exit_code == 0

            deployments = get_deployments()
            assert len(deployments.app_images) == 1
            app_image = deployments.app_images[0]
            assert app_image.flavour_name == "vanilla"
            assert app_image.image.image_string == tag
        finally:
            _cleanup_images()


def test_kabinet_publish_rejects_duplicate():
    """Publishing the same build twice fails: a version/flavour can't be deployed twice."""
    tag = "localhost:5000/com.test.app:0.0.1-vanilla"
    runner = CliRunner()
    with runner.isolated_filesystem():
        _scaffold(runner)
        try:
            with _patched_inspect_all():
                result = runner.invoke(cli, ["plugin", "build"])
            assert result.exit_code == 0, result.output

            with _patched_push():
                first = runner.invoke(cli, ["plugin", "publish", "--tag", tag])
                assert first.exit_code == 0, first.output

                second = runner.invoke(cli, ["plugin", "publish", "--tag", tag])
            assert second.exit_code != 0
            assert "already exists" in second.output
        finally:
            _cleanup_images()
