"""Tests for the `arkitekt-next manifest` command group.

These tests drive the CLI through `--work-dir` (no os.chdir side effects) using
the `app_dir` fixture, which provides a directory with a freshly initialized app.
"""

from click.testing import CliRunner
from arkitekt_next.cli.main import cli
from arkitekt_next.cli.io import load_manifest


def _invoke(work_dir, *args):
    runner = CliRunner()
    # The SDK commands now live under the `app` group (e.g. `arkitekt-next app manifest ...`).
    result = runner.invoke(cli, ["--work-dir", str(work_dir), *args])
    if result.exit_code != 0:
        print(result.output)
        print(result.exception)
    return result


# ---------------------------------------------------------------------------
# manifest version
# ---------------------------------------------------------------------------

def test_manifest_version_set(app_dir):
    result = _invoke(app_dir, "manifest", "version", "set", "2.3.4")
    assert result.exit_code == 0
    assert load_manifest(base_dir=str(app_dir)).version == "2.3.4"


def test_manifest_version_patch(app_dir):
    # app_dir initializes at 0.0.1
    result = _invoke(app_dir, "manifest", "version", "patch")
    assert result.exit_code == 0
    assert load_manifest(base_dir=str(app_dir)).version == "0.0.2"


def test_manifest_version_minor(app_dir):
    result = _invoke(app_dir, "manifest", "version", "minor")
    assert result.exit_code == 0
    assert load_manifest(base_dir=str(app_dir)).version == "0.1.0"


def test_manifest_version_major(app_dir):
    result = _invoke(app_dir, "manifest", "version", "major")
    assert result.exit_code == 0
    assert load_manifest(base_dir=str(app_dir)).version == "1.0.0"


def test_manifest_version_prerelease(app_dir):
    result = _invoke(app_dir, "manifest", "version", "prerelease")
    assert result.exit_code == 0
    # semver bump_prerelease on a release version yields e.g. 0.0.1-rc.1
    assert load_manifest(base_dir=str(app_dir)).version.startswith("0.0.1-")


def test_manifest_version_build(app_dir):
    result = _invoke(app_dir, "manifest", "version", "build")
    assert result.exit_code == 0
    assert "+" in load_manifest(base_dir=str(app_dir)).version


def test_manifest_version_set_prompts_when_no_arg(app_dir):
    """`set` without a version argument prompts, suggesting the next patch."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--work-dir", str(app_dir), "manifest", "version", "set"],
        input="\n",  # accept the suggested default
    )
    assert result.exit_code == 0
    assert load_manifest(base_dir=str(app_dir)).version == "0.0.2"


# ---------------------------------------------------------------------------
# manifest scopes
# ---------------------------------------------------------------------------

def test_manifest_scopes_add(app_dir):
    # app_dir initializes with the default "read" scope
    result = _invoke(app_dir, "manifest", "scopes", "add", "write")
    assert result.exit_code == 0
    scopes = load_manifest(base_dir=str(app_dir)).scopes
    assert "write" in scopes
    assert "read" in scopes


def test_manifest_scopes_add_is_idempotent(app_dir):
    _invoke(app_dir, "manifest", "scopes", "add", "write")
    _invoke(app_dir, "manifest", "scopes", "add", "write")
    scopes = load_manifest(base_dir=str(app_dir)).scopes
    assert scopes.count("write") == 1


def test_manifest_scopes_remove(app_dir):
    _invoke(app_dir, "manifest", "scopes", "add", "write")
    result = _invoke(app_dir, "manifest", "scopes", "remove", "write")
    assert result.exit_code == 0
    assert "write" not in load_manifest(base_dir=str(app_dir)).scopes


def test_manifest_scopes_add_without_arg_errors(app_dir):
    result = _invoke(app_dir, "manifest", "scopes", "add")
    assert result.exit_code != 0
    assert "at least one scope" in result.output


def test_manifest_scopes_add_invalid_choice(app_dir):
    result = _invoke(app_dir, "manifest", "scopes", "add", "doesnotexist")
    assert result.exit_code != 0


def test_manifest_scopes_list(app_dir):
    result = _invoke(app_dir, "manifest", "scopes", "list")
    assert result.exit_code == 0
    assert "read" in result.output


def test_manifest_scopes_available(app_dir):
    result = _invoke(app_dir, "manifest", "scopes", "available")
    assert result.exit_code == 0
    assert "read" in result.output
    assert "write" in result.output


# ---------------------------------------------------------------------------
# manifest inspect
# ---------------------------------------------------------------------------

def test_manifest_inspect(app_dir):
    result = _invoke(app_dir, "manifest", "inspect")
    assert result.exit_code == 0
    assert "com.test.app" in result.output
    assert "0.0.1" in result.output
