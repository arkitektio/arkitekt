"""Tests for `arkitekt-next inspect` and `kabinet validate`.

These exercise commands that introspect an initialized app. They use the
`app_dir` fixture (a directory with a freshly initialized app, driven via
`--work-dir`).
"""

import json
import subprocess
import sys

import pytest
from click.testing import CliRunner
from arkitekt_next.cli.main import cli


# All tests in this file are local CLI tests (no server, no docker). Tagging the
# module with the `cli` marker exempts them from the suite-wide skip in conftest.
pytestmark = pytest.mark.cli


def _invoke(work_dir, *args, **kwargs):
    runner = CliRunner()
    # SDK commands now live under the `app` group.
    result = runner.invoke(cli, ["--work-dir", str(work_dir), *args], **kwargs)
    if result.exit_code != 0:
        print(result.output)
        print(result.exception)
    return result


def _run_cli(work_dir, *args):
    """Run the CLI in a fresh subprocess (clean global registries, cwd on sys.path).

    Uses ``python -m arkitekt_next.cli.main`` with the test's own interpreter so the
    inspect commands import the entrypoint and build the app in isolation — mirroring
    how ``kabinet build`` invokes them.
    """
    result = subprocess.run(
        [
            sys.executable, "-m", "arkitekt_next.cli.main",
            "--work-dir", str(work_dir), *args,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    return result


def _between(text, start, end):
    """Extract and JSON-parse the payload between two stdout markers."""
    return json.loads(text.split(start)[1].split(end)[0])


# ---------------------------------------------------------------------------
# inspect variables
# ---------------------------------------------------------------------------

def test_inspect_variables_clean_app(app_dir):
    """The default `simple` template has no leaking globals."""
    # `inspect variables` imports the entrypoint module by name ("app"). Python
    # caches imported modules in sys.modules, so drop any cached copy from a
    # previous test to make sure we inspect *this* app_dir's entrypoint.
    sys.modules.pop("app", None)

    result = _invoke(app_dir, "inspect", "variables")
    assert result.exit_code == 0
    assert "No dangerous variables found" in result.output


def test_inspect_variables_detects_leaking_global(app_dir):
    """A module-level mutable variable is reported as dangerous."""
    # Overwrite the entrypoint with a deliberately leaking global.
    (app_dir / "app.py").write_text("leaking_state = []\n")
    sys.modules.pop("app", None)

    result = _invoke(app_dir, "inspect", "variables")
    assert result.exit_code == 0
    assert "leaking_state" in result.output


# ---------------------------------------------------------------------------
# inspect requirements / implementations / all (against the `simple` template)
#
# Run in a fresh subprocess so each command builds the app with clean global
# registries (see _run_cli). These exercise the same machine-readable marker
# contract that `kabinet build` relies on.
# ---------------------------------------------------------------------------

# The three functions the default `simple` template registers.
_SIMPLE_FUNCS = ("generate_n_string", "append_world", "print_string")


def test_inspect_requirements(app_dir):
    """`inspect requirements -mr` emits a JSON list between its markers."""
    result = _run_cli(app_dir, "inspect", "requirements", "-mr")
    assert result.returncode == 0, result.stderr

    reqs = _between(result.stdout, "--START_REQUIREMENTS--", "--END_REQUIREMENTS--")
    assert isinstance(reqs, list)  # simple template adds no extra requirements


def test_inspect_implementations(app_dir):
    """`inspect implementations -mr` lists the template's registered functions."""
    result = _run_cli(app_dir, "inspect", "implementations", "-mr")
    assert result.returncode == 0, result.stderr

    impls = _between(result.stdout, "--START_TEMPLATES--", "--END_TEMPLATES--")
    assert isinstance(impls, list)
    assert len(impls) >= 3
    for name in _SIMPLE_FUNCS:
        assert name in result.stdout


def test_inspect_all(app_dir):
    """`inspect all -mr` emits the full agent manifest with the expected sections."""
    result = _run_cli(app_dir, "inspect", "all", "-mr")
    assert result.returncode == 0, result.stderr

    agent = _between(result.stdout, "--START_AGENT--", "--END_AGENT--")
    assert isinstance(agent, dict)
    for key in ("states", "implementations", "locks", "requirements", "bloks"):
        assert key in agent
    assert len(agent["implementations"]) >= 3
    for name in _SIMPLE_FUNCS:
        assert name in result.stdout


def test_inspect_all_pretty(app_dir):
    """`inspect all --pretty` (no markers) exits cleanly and prints the manifest.

    The pretty branch routes through rich's console, which word-wraps output, so we
    smoke-test it rather than JSON-parsing the (potentially reflowed) text.
    """
    result = _run_cli(app_dir, "inspect", "all", "--pretty")
    assert result.returncode == 0, result.stderr
    assert "implementations" in result.stdout
    assert "states" in result.stdout


# ---------------------------------------------------------------------------
# kabinet validate
# ---------------------------------------------------------------------------

def test_kabinet_validate(app_dir):
    """After scaffolding a flavour, validate reports it as valid."""
    # Flavours are scaffolded via the top-level `plugin init` (not under `app`).
    init_result = CliRunner().invoke(
        cli,
        ["--work-dir", str(app_dir), "plugin", "init",
         "--flavour", "vanilla", "--arkitekt-version", "0.0.1"],
        input="n\n",  # decline the devcontainer prompt
    )
    assert init_result.exit_code == 0, init_result.output

    result = CliRunner().invoke(cli, ["--work-dir", str(app_dir), "plugin", "validate"])
    assert result.exit_code == 0
    assert "vanilla" in result.output
    assert "All flavours are valid" in result.output


def test_kabinet_validate_without_flavours_errors(app_dir):
    """validate fails cleanly when no flavours folder exists yet."""
    result = CliRunner().invoke(cli, ["--work-dir", str(app_dir), "plugin", "validate"])
    assert result.exit_code != 0
    assert "plugin init" in result.output


# ---------------------------------------------------------------------------
# --help smoke tests — every command group exposes its help text
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "args",
    [
        [],
        ["init"],
        ["run"],
        ["gen"],
        ["plugin"],
        ["manifest"],
        ["manifest", "version"],
        ["manifest", "scopes"],
        ["inspect"],
        ["call"],
    ],
)
def test_help_for_command_groups(args):
    runner = CliRunner()
    result = runner.invoke(cli, [*args, "--help"])
    assert result.exit_code == 0, result.output
    assert "Usage" in result.output or "Options" in result.output
