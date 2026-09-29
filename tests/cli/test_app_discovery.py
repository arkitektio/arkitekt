"""The CLI finds the App a module declares, the way uvicorn finds a module's ``app``.

A target is ``module[:attr]`` or a file path, relative to ``--work-dir``, and
defaults to ``app`` (or ``$ARKITEKT_APP``). There is no manifest: the identity
the CLI works with is read off the App. Nothing here connects anywhere.
"""

import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from typer.testing import CliRunner

from arkitekt import App
from arkitekt.cli.main import cli_app
from arkitekt.cli.target import (
    DEFAULT_TARGET,
    NoAppError,
    TargetError,
    find_app,
    load_target,
    parse_target,
    require_app,
)

APP_STYLE = '''
from arkitekt import App, run

app = App("chosen-by-the-module", "1.2.3", author="someone", scopes=["read"])


@app.action
def from_the_app(x: int) -> int:
    """Declared on the app."""
    return x


@app.startup
async def boot():
    """A startup hook on the app."""


if __name__ == "__main__":
    run(app)
'''

def _run_cli(work_dir, *args, env=None):
    return subprocess.run(
        [sys.executable, "-m", "arkitekt.cli.main", "--work-dir", str(work_dir), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def _between(text, start, end):
    return json.loads(text.split(start)[1].split(end)[0])


def module_with(**attributes) -> ModuleType:
    module = ModuleType("entrypoint")
    vars(module).update(attributes)
    return module


# --------------------------------------------------------------------------- #
# Parsing a target
# --------------------------------------------------------------------------- #


def test_the_default_target_is_the_module_app(tmp_path):
    assert DEFAULT_TARGET == "app"
    target = parse_target(DEFAULT_TARGET, str(tmp_path))

    assert (target.module, target.attribute) == ("app", None)
    assert target.file == str((tmp_path / "app.py").resolve())


def test_a_module_target_may_name_the_attribute(tmp_path):
    target = parse_target("pkg.main:api", str(tmp_path))

    assert (target.module, target.attribute) == ("pkg.main", "api")
    assert target.file == str((tmp_path / "pkg" / "main.py").resolve())


@pytest.mark.parametrize("raw", ["app.py", "./app.py", "app.py:app"])
def test_a_file_target_is_its_module(tmp_path, raw):
    target = parse_target(raw, str(tmp_path))

    assert target.module == "app"
    assert target.attribute == ("app" if raw.endswith(":app") else None)


def test_a_file_target_in_a_subdirectory_is_a_dotted_module(tmp_path):
    target = parse_target("src/tools/app.py:api", str(tmp_path))

    assert (target.module, target.attribute) == ("src.tools.app", "api")


def test_an_absolute_file_target_is_relative_to_the_work_dir(tmp_path):
    target = parse_target(str(tmp_path / "app.py"), str(tmp_path))

    assert target.module == "app"


def test_a_package_target_watches_its_init(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")

    found = Path(parse_target("pkg", str(tmp_path)).file)
    assert found.resolve() == (tmp_path / "pkg" / "__init__.py").resolve()


@pytest.mark.parametrize("raw", ["", "  ", "app:", "not a module", "1app"])
def test_malformed_targets_are_refused(tmp_path, raw):
    with pytest.raises(TargetError):
        parse_target(raw, str(tmp_path))


def test_a_file_outside_the_work_dir_is_refused(tmp_path):
    with pytest.raises(TargetError, match="not inside the work dir"):
        parse_target("/somewhere/else/app.py", str(tmp_path / "project"))


# --------------------------------------------------------------------------- #
# Finding the App in a module
# --------------------------------------------------------------------------- #


def test_a_module_without_an_app_has_none_to_find():
    assert find_app(module_with(something=1)) is None
    assert find_app(None) is None


def test_the_app_named_app_wins():
    main, other = App("main"), App("other")

    assert find_app(module_with(app=main, worker=other)) is main


def test_one_app_under_any_name_is_found_and_several_are_ambiguous():
    only, second = App("only"), App("second")

    assert find_app(module_with(application=only, alias=only)) is only
    with pytest.raises(ValueError, match="several apps.*first.*second"):
        find_app(module_with(first=only, second=second))


def test_the_named_attribute_is_taken_even_among_several():
    first, second = App("first"), App("second")

    assert find_app(module_with(first=first, second=second), "second") is second


def test_named_attribute_must_be_an_app():
    with pytest.raises(NoAppError, match="not an arkitekt App"):
        find_app(module_with(app=object()), "app")
    with pytest.raises(NoAppError, match="has no attribute 'missing'"):
        find_app(module_with(app=App("x")), "missing")


def test_a_module_without_an_app_is_an_error_that_shows_the_new_api():
    with pytest.raises(NoAppError, match=r"(?s)defines no arkitekt App.*App\(.*@app\.action.*run\(app\)"):
        require_app(module_with(something=1))


# --------------------------------------------------------------------------- #
# Loading a target from a work dir
# --------------------------------------------------------------------------- #


def test_load_target_imports_the_work_dirs_module(tmp_path, monkeypatch):
    (tmp_path / "myapp.py").write_text(APP_STYLE)
    monkeypatch.syspath_prepend(str(tmp_path))

    app, module, target = load_target("myapp.py", str(tmp_path))

    assert module.__name__ == "myapp" and target.module == "myapp"
    assert (app.identifier, app.version, app.author) == ("chosen-by-the-module", "1.2.3", "someone")


def test_load_target_prefers_the_work_dir_over_a_cached_module(tmp_path, monkeypatch):
    """A module of the same name imported from elsewhere must not shadow --work-dir."""
    first, second = tmp_path / "one", tmp_path / "two"
    for directory, identifier in ((first, "first"), (second, "second")):
        directory.mkdir()
        (directory / "shadowed.py").write_text(f"from arkitekt import App\napp = App({identifier!r})\n")

    monkeypatch.syspath_prepend(str(first))
    assert load_target("shadowed", str(first))[0].identifier == "first"

    monkeypatch.syspath_prepend(str(second))
    assert load_target("shadowed", str(second))[0].identifier == "second"
    sys.modules.pop("shadowed", None)


# --------------------------------------------------------------------------- #
# The commands resolve targets the same way
# --------------------------------------------------------------------------- #


def _requirements_via_cli(work_dir, *args, **kwargs):
    result = CliRunner().invoke(
        cli_app, ["--work-dir", str(work_dir), "inspect", "requirements", *args, "-mr"], **kwargs
    )
    return result


@pytest.mark.parametrize("target", [None, "app", "app:app", "app.py", "app.py:app"])
def test_every_target_form_reaches_the_same_app(app_dir, target):
    args = [target] if target else []
    result = _requirements_via_cli(app_dir, *args)

    assert result.exit_code == 0, result.output
    assert "--START_REQUIREMENTS--" in result.output


def test_the_target_can_come_from_the_environment(app_dir):
    (app_dir / "other.py").write_text("from arkitekt import App\napi = App('from-env')\n")

    ok = _requirements_via_cli(app_dir, env={"ARKITEKT_APP": "other:api"})
    missing = _requirements_via_cli(app_dir, env={"ARKITEKT_APP": "nowhere"})

    assert ok.exit_code == 0, ok.output
    assert missing.exit_code != 0
    assert "Could not find the app module 'nowhere'" in missing.output


def test_an_ambiguous_module_is_an_error_naming_the_choices(app_dir):
    (app_dir / "twice.py").write_text(
        "from arkitekt import App\nfirst = App('one')\nsecond = App('two')\n"
    )

    result = _requirements_via_cli(app_dir, "twice")

    assert result.exit_code != 0
    assert "several apps (first, second)" in result.output
    assert "twice:first" in result.output


def test_a_module_without_an_app_is_a_clean_error(app_dir):
    (app_dir / "empty.py").write_text("VALUE = 1\n")

    result = _requirements_via_cli(app_dir, "empty")

    assert result.exit_code != 0
    assert "defines no arkitekt App" in result.output
    assert "@app.action" in result.output


# --------------------------------------------------------------------------- #
# End to end, in a fresh interpreter
# --------------------------------------------------------------------------- #


def test_inspect_reports_what_was_declared_on_the_modules_app(app_dir):
    (app_dir / "app.py").write_text(APP_STYLE)

    result = _run_cli(app_dir, "inspect", "implementations", "-mr")
    assert result.returncode == 0, result.stderr

    impls = _between(result.stdout, "--START_TEMPLATES--", "--END_TEMPLATES--")
    assert [impl["interface"] for impl in impls] == ["from_the_app"]
    assert [port["key"] for port in impls[0]["definition"]["args"]] == ["x"]


def test_inspect_lifecycle_reads_the_apps_hooks(app_dir):
    (app_dir / "app.py").write_text(APP_STYLE)

    result = _run_cli(app_dir, "inspect", "lifecycle", "-mr")
    assert result.returncode == 0, result.stderr

    lifecycle = _between(result.stdout, "--START_LIFECYCLE--", "--END_LIFECYCLE--")
    assert [hook["name"] for hook in lifecycle["startup"]] == ["boot"]


def test_inspect_structures_reads_the_apps_own_registry(app_dir):
    (app_dir / "app.py").write_text(APP_STYLE)

    result = _run_cli(app_dir, "inspect", "structures", "-mr")
    assert result.returncode == 0, result.stderr

    structures = _between(result.stdout, "--START_STRUCTURES--", "--END_STRUCTURES--")
    assert "@rekuest/implementation" in {item["identifier"] for item in structures}
    assert {item["service"] for item in structures} == {"rekuest"}
