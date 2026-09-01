from click.testing import CliRunner
from arkitekt_next.cli.main import cli
import os
from unittest.mock import patch
import pytest


# ---------------------------------------------------------------------------
# init command — using isolated_filesystem (legacy style, still valid)
# ---------------------------------------------------------------------------

def test_init_uv():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/uv"

            result = runner.invoke(cli, ["init", "--package-manager", "uv", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])
            if result.exit_code != 0:
                print(result.output)
                print(result.exception)
            assert result.exit_code == 0

            assert mock_run.call_count == 2
            mock_run.assert_any_call(["uv", "init", "--name", "com.test.app", "--no-workspace"], check=True, cwd=os.getcwd())
            mock_run.assert_any_call(["uv", "add", "arkitekt-next[all]"], check=True, cwd=os.getcwd())

            assert os.path.exists("app.py")
            assert os.path.exists(".arkitekt_next/manifest.yaml")

            with open(".arkitekt_next/manifest.yaml") as f:
                content = f.read()
                assert "package_manager: uv" in content


def test_init_yes():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["init", "--yes", "--package-manager", "pip"])
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0
        assert os.path.exists("app.py")
        assert os.path.exists(".arkitekt_next/manifest.yaml")


def test_init_path():
    runner = CliRunner()
    with runner.isolated_filesystem():
        original_cwd = os.getcwd()
        result = runner.invoke(cli, ["init", "myapp", "--package-manager", "pip", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"], input="\n")
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0

        assert os.path.exists(os.path.join(original_cwd, "myapp", "app.py"))
        assert os.path.exists(os.path.join(original_cwd, "myapp", ".arkitekt_next", "manifest.yaml"))

        with open(os.path.join(original_cwd, "myapp", ".arkitekt_next", "manifest.yaml")) as f:
            content = f.read()
            assert "identifier: myapp" in content


def test_init_default_uv():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/uv"

            result = runner.invoke(cli, ["init", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])

            assert result.exit_code == 0
            assert mock_run.call_count == 2
            mock_run.assert_any_call(["uv", "init", "--name", "com.test.app", "--no-workspace"], check=True, cwd=os.getcwd())


def test_init_default_pip():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            result = runner.invoke(cli, ["init", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])

            assert result.exit_code == 0
            assert os.path.exists("app.py")
            assert not os.path.exists("pyproject.toml")


def test_init_uv_not_installed():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            result = runner.invoke(cli, ["init", "--package-manager", "uv", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])
            assert result.exit_code != 0
            assert "uv is not installed" in result.output


# ---------------------------------------------------------------------------
# init command — using --work-dir (new style, no os.chdir side effects)
# ---------------------------------------------------------------------------

def test_init_work_dir(tmp_path):
    """init with --work-dir writes to tmp_path without touching process CWD."""
    original_cwd = os.getcwd()
    runner = CliRunner()

    result = runner.invoke(cli, [
        "--work-dir", str(tmp_path),
        "init",
        "--identifier", "com.workdir.app",
        "--version", "0.1.0",
        "--author", "tester",
        "--entrypoint", "app",
        "--package-manager", "pip",
    ])
    if result.exit_code != 0:
        print(result.output)
        print(result.exception)
    assert result.exit_code == 0

    # Files were created in tmp_path, not in the original cwd
    assert (tmp_path / "app.py").exists()
    assert (tmp_path / ".arkitekt_next" / "manifest.yaml").exists()
    assert os.getcwd() == original_cwd, "Process CWD must not change"

    with open(tmp_path / ".arkitekt_next" / "manifest.yaml") as f:
        content = f.read()
        assert "identifier: com.workdir.app" in content


def test_init_subdir_work_dir(tmp_path):
    """init <subdir> with --work-dir creates a sub-directory inside work_dir."""
    original_cwd = os.getcwd()
    runner = CliRunner()

    result = runner.invoke(cli, [
        "--work-dir", str(tmp_path),
        "init", "mysubapp",
        "--identifier", "com.sub.app",
        "--version", "0.1.0",
        "--author", "tester",
        "--entrypoint", "app",
        "--package-manager", "pip",
    ])
    if result.exit_code != 0:
        print(result.output)
        print(result.exception)
    assert result.exit_code == 0

    assert (tmp_path / "mysubapp" / "app.py").exists()
    assert (tmp_path / "mysubapp" / ".arkitekt_next" / "manifest.yaml").exists()
    assert os.getcwd() == original_cwd


# ---------------------------------------------------------------------------
# kabinet commands — rely on app_runner fixture (--work-dir based)
# ---------------------------------------------------------------------------

def test_kabinet_init():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(cli, ["init", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])

        result = runner.invoke(cli, ["plugin", "init", "--flavour", "vanilla", "--devcontainer", "--arkitekt-version", "0.0.1"])
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0
        assert os.path.exists(".arkitekt_next/flavours/vanilla/Dockerfile")
        assert os.path.exists(".devcontainer/vanilla/devcontainer.json")

        with open(".devcontainer/vanilla/devcontainer.json") as f:
            content = f.read()
            assert "ms-python.python" in content


def test_kabinet_init_uv():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(cli, ["init", "--package-manager", "uv", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])

        result = runner.invoke(cli, ["plugin", "init", "--flavour", "uv_flavour", "--devcontainer", "--arkitekt-version", "0.0.1"])
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0
        assert os.path.exists(".arkitekt_next/flavours/uv_flavour/Dockerfile")

        with open(".arkitekt_next/flavours/uv_flavour/Dockerfile") as f:
            content = f.read()
            assert "COPY --from=ghcr.io/astral-sh/uv" in content


def test_kabinet_flavour_commands():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(cli, ["init", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])

        result = runner.invoke(cli, ["plugin", "flavour", "add", "--flavour", "gpu", "--description", "GPU flavour"], input="n\n")
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0
        assert os.path.exists(".arkitekt_next/flavours/gpu/config.yaml")

        result = runner.invoke(cli, ["plugin", "selector", "add", "gpu", "--kind", "cuda", "--cuda-cores", "100"])
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0

        with open(".arkitekt_next/flavours/gpu/config.yaml") as f:
            content = f.read()
            assert "kind: cuda" in content
            assert "cuda_cores: 100" in content


# ---------------------------------------------------------------------------
# kabinet commands — work-dir style
# ---------------------------------------------------------------------------

def test_kabinet_init_work_dir(tmp_path):
    """kabinet init via --work-dir, no os.chdir."""
    original_cwd = os.getcwd()
    runner = CliRunner()

    runner.invoke(cli, [
        "--work-dir", str(tmp_path),
        "init",
        "--identifier", "com.test.app",
        "--version", "0.0.1",
        "--author", "me",
        "--entrypoint", "app",
        "--package-manager", "pip",
    ])

    result = runner.invoke(cli, [
        "--work-dir", str(tmp_path),
        "plugin", "init",
        "--flavour", "vanilla",
        "--devcontainer",
        "--arkitekt-version", "0.0.1",
    ])
    if result.exit_code != 0:
        print(result.output)
        print(result.exception)
    assert result.exit_code == 0
    assert (tmp_path / ".arkitekt_next" / "flavours" / "vanilla" / "Dockerfile").exists()
    assert os.getcwd() == original_cwd


# ---------------------------------------------------------------------------
# manifest commands — work-dir style
# ---------------------------------------------------------------------------

def test_manifest_version(tmp_path):
    """manifest version set via --work-dir."""
    runner = CliRunner()
    runner.invoke(cli, [
        "--work-dir", str(tmp_path),
        "init",
        "--identifier", "com.test.app",
        "--version", "0.0.1",
        "--author", "me",
        "--entrypoint", "app",
        "--package-manager", "pip",
    ])

    result = runner.invoke(cli, [
        "--work-dir", str(tmp_path),
        "manifest", "version", "set", "1.2.3",
    ])
    if result.exit_code != 0:
        print(result.output)
        print(result.exception)
    assert result.exit_code == 0

    with open(tmp_path / ".arkitekt_next" / "manifest.yaml") as f:
        content = f.read()
        assert "1.2.3" in content
