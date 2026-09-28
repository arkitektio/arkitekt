import importlib.util
import os
import sys
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from arkitekt import App
from arkitekt.cli.commands.app.init.main import render_app_arguments, render_template
from arkitekt.cli.constants import compile_templates
from arkitekt.cli.main import cli_app
from arkitekt.cli.utils import build_relative_dir

from .isolation import isolated_filesystem


# ---------------------------------------------------------------------------
# init command — using isolated_filesystem (legacy style, still valid)
# ---------------------------------------------------------------------------

def test_init_uv():
    runner = CliRunner()
    with isolated_filesystem():
        with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/uv"

            result = runner.invoke(cli_app, ["init", "--package-manager", "uv", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])
            if result.exit_code != 0:
                print(result.output)
                print(result.exception)
            assert result.exit_code == 0

            assert mock_run.call_count == 2
            mock_run.assert_any_call(["uv", "init", "--name", "com.test.app", "--no-workspace"], check=True, cwd=os.getcwd())
            mock_run.assert_any_call(["uv", "add", "arkitekt[all]"], check=True, cwd=os.getcwd())

            assert os.path.exists("app.py")
            assert not os.path.exists(".arkitekt/manifest.yaml")


def test_init_yes():
    runner = CliRunner()
    with isolated_filesystem():
        result = runner.invoke(cli_app, ["init", "--yes", "--package-manager", "pip"])
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0
        assert os.path.exists("app.py")
        assert not os.path.exists(".arkitekt")


def test_init_path():
    runner = CliRunner()
    with isolated_filesystem():
        original_cwd = os.getcwd()
        result = runner.invoke(cli_app, ["init", "myapp", "--package-manager", "pip", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"], input="\n")
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0

        assert os.path.exists(os.path.join(original_cwd, "myapp", "app.py"))
        assert not os.path.exists(os.path.join(original_cwd, "myapp", ".arkitekt", "manifest.yaml"))

        # The identifier prompt defaults to the directory name, and lands in the App.
        with open(os.path.join(original_cwd, "myapp", "app.py")) as f:
            assert "App('myapp', '0.0.1', author='me'" in f.read()


def test_init_default_uv():
    runner = CliRunner()
    with isolated_filesystem():
        with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/uv"

            result = runner.invoke(cli_app, ["init", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])

            assert result.exit_code == 0
            assert mock_run.call_count == 2
            mock_run.assert_any_call(["uv", "init", "--name", "com.test.app", "--no-workspace"], check=True, cwd=os.getcwd())


def test_init_default_pip():
    runner = CliRunner()
    with isolated_filesystem():
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            result = runner.invoke(cli_app, ["init", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])

            assert result.exit_code == 0
            assert os.path.exists("app.py")
            assert not os.path.exists("pyproject.toml")


def test_init_uv_not_installed():
    runner = CliRunner()
    with isolated_filesystem():
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            result = runner.invoke(cli_app, ["init", "--package-manager", "uv", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])
            assert result.exit_code != 0
            assert "uv is not installed" in result.output


# ---------------------------------------------------------------------------
# init command — using --work-dir (new style, no os.chdir side effects)
# ---------------------------------------------------------------------------

def test_init_work_dir(tmp_path):
    """init with --work-dir writes to tmp_path without touching process CWD."""
    original_cwd = os.getcwd()
    runner = CliRunner()

    result = runner.invoke(cli_app, [
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
    assert os.getcwd() == original_cwd, "Process CWD must not change"

    # The entrypoint is the only file: the identity is the App in it.
    assert sorted(p.name for p in tmp_path.iterdir()) == ["app.py"]
    assert "App('com.workdir.app', '0.1.0', author='tester'" in (tmp_path / "app.py").read_text()


def test_init_subdir_work_dir(tmp_path):
    """init <subdir> with --work-dir creates a sub-directory inside work_dir."""
    original_cwd = os.getcwd()
    runner = CliRunner()

    result = runner.invoke(cli_app, [
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
    assert not (tmp_path / "mysubapp" / ".arkitekt").exists()
    assert os.getcwd() == original_cwd


# ---------------------------------------------------------------------------
# kabinet commands — rely on app_runner fixture (--work-dir based)
# ---------------------------------------------------------------------------

def test_kabinet_init():
    runner = CliRunner()
    with isolated_filesystem():
        runner.invoke(cli_app, ["init", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])

        result = runner.invoke(cli_app, ["plugin", "init", "--flavour", "vanilla", "--devcontainer", "--arkitekt-version", "0.0.1"])
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0
        assert os.path.exists(".arkitekt/flavours/vanilla/Dockerfile")
        assert os.path.exists(".devcontainer/vanilla/devcontainer.json")

        with open(".devcontainer/vanilla/devcontainer.json") as f:
            content = f.read()
            assert "ms-python.python" in content


def test_kabinet_init_uv():
    runner = CliRunner()
    with isolated_filesystem():
        runner.invoke(cli_app, ["init", "--package-manager", "uv", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])

        result = runner.invoke(cli_app, ["plugin", "init", "--flavour", "uv_flavour", "--devcontainer", "--arkitekt-version", "0.0.1"])
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0
        assert os.path.exists(".arkitekt/flavours/uv_flavour/Dockerfile")

        with open(".arkitekt/flavours/uv_flavour/Dockerfile") as f:
            content = f.read()
            assert "COPY --from=ghcr.io/astral-sh/uv" in content


def test_kabinet_flavour_commands():
    runner = CliRunner()
    with isolated_filesystem():
        runner.invoke(cli_app, ["init", "--identifier", "com.test.app", "--version", "0.0.1", "--author", "me", "--entrypoint", "app"])

        result = runner.invoke(cli_app, ["plugin", "flavour", "add", "--flavour", "gpu", "--description", "GPU flavour"], input="n\n")
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0
        assert os.path.exists(".arkitekt/flavours/gpu/config.yaml")

        result = runner.invoke(cli_app, ["plugin", "selector", "add", "gpu", "--kind", "cuda", "--cuda-cores", "100"])
        if result.exit_code != 0:
            print(result.output)
            print(result.exception)
        assert result.exit_code == 0

        with open(".arkitekt/flavours/gpu/config.yaml") as f:
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

    runner.invoke(cli_app, [
        "--work-dir", str(tmp_path),
        "init",
        "--identifier", "com.test.app",
        "--version", "0.0.1",
        "--author", "me",
        "--entrypoint", "app",
        "--package-manager", "pip",
    ])

    result = runner.invoke(cli_app, [
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
    assert (tmp_path / ".arkitekt" / "flavours" / "vanilla" / "Dockerfile").exists()
    assert os.getcwd() == original_cwd


# ---------------------------------------------------------------------------
# init writes the App's identity into the entrypoint
# ---------------------------------------------------------------------------

def _import_file(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"{path} is not an importable file"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


@pytest.mark.parametrize("template", compile_templates())
def test_every_template_scaffolds_an_importable_app(tmp_path, template):
    result = CliRunner().invoke(cli_app, [
        "--work-dir", str(tmp_path),
        "init",
        "--identifier", "com.example.thing",
        "--version", "1.2.3",
        "--author", "Jane O'Neil",
        "--scopes", "read", "--scopes", "write",
        "--logo", "https://example.com/logo.png",
        "--template", template,
        "--entrypoint", "main",
        "--package-manager", "pip",
    ])
    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in tmp_path.iterdir()) == ["main.py"]

    module = _import_file(tmp_path / "main.py", f"scaffolded_{template}")

    app = module.app
    assert isinstance(app, App)
    assert (app.identifier, app.version, app.author) == ("com.example.thing", "1.2.3", "Jane O'Neil")
    assert app.scopes == ["read", "write"]
    assert app.logo == "https://example.com/logo.png"
    # What it declares is valid: the snapshot a run would take succeeds.
    assert app.snapshot().registry.get_implementations()


def test_the_scaffolded_app_is_what_the_commands_find(tmp_path):
    result = CliRunner().invoke(cli_app, [
        "--work-dir", str(tmp_path), "init", "--yes", "--identifier", "com.found.app",
        "--package-manager", "pip",
    ])
    assert result.exit_code == 0, result.output

    result = CliRunner().invoke(cli_app, ["--work-dir", str(tmp_path), "inspect", "implementations", "-mr"])
    assert result.exit_code == 0, result.output
    assert "generate_n_string" in result.output


def test_templates_keep_their_port_references():
    """Filling a template must not `str.format` it: `{{n}}` is a port reference."""
    with open(build_relative_dir("templates", "simple.py")) as f:
        source = f.read()

    rendered = render_template(source, render_app_arguments("x", "0.0.1"))

    assert "{{n}}" in rendered and "App('x', '0.0.1')" in rendered


def test_app_arguments_quote_anything():
    arguments = render_app_arguments('we"ird', "0.0.1", author="a'b", scopes=["read"])

    # It is Python source for the App(...) call: evaluating it gives the values back.
    assert eval(f"(lambda *args, **kwargs: (args, kwargs))({arguments})") == (
        ('we"ird', "0.0.1"),
        {"author": "a'b", "scopes": ["read"]},
    )


def test_init_has_no_manifest_options():
    result = CliRunner().invoke(cli_app, ["init", "--help"])

    assert "--overwrite-manifest" not in result.output
