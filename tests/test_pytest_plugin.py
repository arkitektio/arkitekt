"""Tests for the pytest plugin this package exports.

``arkitekt_next.pytest`` auto-loads into every downstream project via the
``pytest11`` entry point, so a mistake here breaks other people's test suites
silently. It previously shipped a ``running_server`` fixture that invoked lok's
``validatecode`` with a *positional* code, which the management command does not
accept -- so the shipped fixture could never have worked. Nothing caught it,
because the plugin had no tests at all.

These tests are deliberately docker-free: they check the plugin's wiring (what it
registers, what it advertises, how it talks to lok) rather than booting a stack.
The docker-backed behaviour is covered by the ``integration`` suite.
"""

import inspect

import pytest

from arkitekt_next.pytest import fixtures as plugin


def _marker(fixture):
    """The fixture's marker, across pytest versions.

    pytest <8.4 stashes it on ``_pytestfixturefunction``; 8.4+ wraps the function in
    a ``FixtureFunctionDefinition`` carrying ``_fixture_function_marker``.
    """
    for attr in ("_pytestfixturefunction", "_fixture_function_marker"):
        marker = getattr(fixture, attr, None)
        if marker is not None:
            return marker
    raise AssertionError(f"{fixture!r} is not a pytest fixture")


def _unwrap(fixture):
    """The undecorated function behind a fixture, across pytest versions."""
    getter = getattr(fixture, "_get_wrapped_function", None)
    if getter is not None:
        return getter()
    return fixture.__wrapped__


def test_plugin_is_registered_as_an_entry_point():
    """The plugin must actually be exported, or none of this ships."""
    from importlib.metadata import entry_points

    eps = {ep.name: ep.value for ep in entry_points(group="pytest11")}
    assert eps.get("arkitekt_next") == "arkitekt_next.pytest"


@pytest.mark.parametrize(
    "name",
    ["arkitekt_server", "lok_server", "running_server", "running_app", "arkitekt_channel"],
)
def test_exports_its_fixtures(name):
    """Every advertised fixture exists and is a real pytest fixture."""
    assert _marker(getattr(plugin, name)) is not None


def test_fixtures_are_session_scoped():
    """Booting a stack is expensive; these must not run per-test."""
    for name in ("arkitekt_server", "lok_server", "running_server", "running_app"):
        assert _marker(getattr(plugin, name)).scope == "session", (
            f"{name} should be session-scoped"
        )


def test_device_code_approval_uses_the_lok_controller():
    """The device-code hook must go through ``LokController``, not a raw command.

    This is the regression guard for the shipped bug: the old fixture hand-wrote
    ``manage.py validatecode {code} ...`` with the code as a positional argument,
    which lok rejects. ``LokController.avalidate_device_code`` passes ``--code``.
    """
    source = inspect.getsource(_unwrap(plugin.running_app))
    assert "avalidate_device_code" in source
    # ... and must not go back to hand-rolling the management command.
    assert "manage.py" not in source


def test_lok_controller_passes_the_code_as_a_flag():
    """``validatecode`` takes ``--code``; a positional code is silently wrong."""
    from arkitekt_next.server.lok import LokController

    args = LokController._validate_args("CODE123", "demo", "arkitektio", "localhost")
    assert "--code CODE123" in args
    assert "--user demo" in args
    assert "--org arkitektio" in args
    assert "--hub localhost" in args
    # A positional code would look like `validatecode CODE123`.
    assert not args.startswith("validatecode CODE123")


def test_registers_its_markers_in_this_repo(pytestconfig):
    """Sanity check only -- this repo's ``pyproject.toml`` also declares them.

    ``addinivalue_line`` appends to the same ini value, so this passes whether or
    not the plugin registered anything. The claim that *downstream* projects get
    the markers is proven by ``test_a_downstream_project_gets_the_fixtures``,
    which runs with ``--strict-markers`` where no ini file exists.
    """
    markers = "\n".join(pytestconfig.getini("markers"))
    assert "integration:" in markers
    assert "needs_docker:" in markers


def test_channel_option_is_available():
    """The plugin advertises the image channel it will pull."""
    assert plugin.DEFAULT_CHANNEL == "next"


def test_docker_available_is_falsy_without_a_daemon(monkeypatch):
    """The docker probe must not raise when docker is missing -- it gates skips."""
    monkeypatch.setattr(plugin.shutil, "which", lambda _: None)
    assert plugin.docker_available() is False


def test_factory_signature_supports_kinds_and_services():
    """The factory is the documented way to pick a stack shape."""
    source = inspect.getsource(_unwrap(plugin.arkitekt_server))
    assert "kind" in source and "services" in source


def test_a_downstream_project_gets_the_fixtures(tmp_path):
    """End-to-end: a fresh pytest run outside this repo resolves the fixtures.

    This is the check that would have caught the shipped breakage. It runs pytest
    in a clean directory -- no conftest of ours, no ini file, no rootdir tricks --
    so the only way ``arkitekt_server`` resolves, and the only place the markers
    can come from, is the ``pytest11`` entry point.

    ``--strict-markers`` turns an unregistered marker into an error, which is what
    makes this decisive about ``pytest_configure`` actually running.

    The factory is requested but never *called*, so no container is started.
    """
    import subprocess
    import sys

    (tmp_path / "test_downstream.py").write_text(
        "import pytest\n"
        "\n"
        "@pytest.mark.integration\n"
        "@pytest.mark.needs_docker\n"
        "def test_fixture_resolves(arkitekt_server):\n"
        "    assert callable(arkitekt_server)\n"
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "--strict-markers",
            "-q",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=120,
    )
    combined = result.stdout + result.stderr

    assert "fixture 'arkitekt_server' not found" not in combined, combined
    # --strict-markers reports these as errors if pytest_configure did not run.
    assert "not found in `markers` configuration" not in combined, combined
    assert result.returncode == 0, combined
