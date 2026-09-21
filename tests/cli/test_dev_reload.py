"""What `arkitekt run dev` reloads when code changes, and what it runs then.

A reload has to re-run the entrypoint: it is what declares the App, and only
re-running it declares a new one from the changed code. Reloading only the changed
dependencies would hand back the old App, still holding the old functions.
"""

import asyncio
import io
import sys

import pytest

from arkitekt.cli.commands.app.run import dev as dev_module
from arkitekt.cli.commands.app.run.dev import (
    _start,
    modules_to_reload,
    reload_modules,
)
from arkitekt.cli.target import import_target, parse_target
from rich.console import Console


def test_deep_mode_reloads_the_entrypoint_even_when_only_a_dependency_changed() -> None:
    assert modules_to_reload({"mypkg.helpers"}, "app", deep=True) == ["mypkg.helpers", "app"]


def test_the_entrypoint_is_reloaded_last_and_once() -> None:
    order = modules_to_reload({"app", "b", "a"}, "app", deep=True)

    assert order == ["a", "b", "app"]


def test_shallow_mode_reloads_only_the_entrypoint() -> None:
    assert modules_to_reload({"ignored"}, "app", deep=False) == ["app"]


def _declare(path, identifier: str) -> None:
    path.write_text(
        "from arkitekt import App\n"
        f"app = App({identifier!r})\n\n"
        "@app.action\n"
        "def f(x: int) -> int:\n"
        "    return x\n"
    )


async def _started(*args):
    """Start a run the way the dev loop does, and wait for it to finish."""
    run = _start(*args)
    assert run is not None
    await run


def test_a_reload_runs_the_new_app_with_the_same_connection_flags(tmp_path, monkeypatch):
    """The App is looked up again after a reload; the flags go to the runner each time."""
    runs = []

    async def fake_arun(app, **options):
        runs.append((app, options))

    monkeypatch.setattr("arkitekt.runtime.arun", fake_arun)
    monkeypatch.syspath_prepend(str(tmp_path))
    entry = tmp_path / "devreloaded.py"
    _declare(entry, "before")
    target = parse_target("devreloaded", str(tmp_path))
    console = Console(file=io.StringIO())

    async def scenario():
        module = import_target(target)
        await _started(console, module, target, {"url": "http://x"}, "initial")
        # A different length, so the bytecode cache cannot mistake it for the old file.
        _declare(entry, "after the change")
        reload_modules(modules_to_reload(set(), target.module, deep=False))
        await _started(console, sys.modules[target.module], target, {"url": "http://x"}, "reloaded")

    try:
        asyncio.run(scenario())
    finally:
        sys.modules.pop("devreloaded", None)

    assert [app.identifier for app, _ in runs] == ["before", "after the change"]
    assert runs[0][0] is not runs[1][0]
    assert all(options == {"url": "http://x"} for _, options in runs)


def test_dev_hands_the_explicit_flags_to_the_loop(app_dir, monkeypatch):
    from click.testing import CliRunner

    from arkitekt.cli.main import cli

    seen = {}

    async def fake_run_dev(console, target, work_dir, options=None, deep=False, context=None, context_file=None):
        seen.update(target=target, work_dir=work_dir, options=options, deep=deep, context=context)

    monkeypatch.setattr(dev_module, "run_dev", fake_run_dev)

    result = CliRunner().invoke(
        cli,
        ["--work-dir", str(app_dir), "run", "dev", "app.py", "--url", "http://u", "--reauth", "-l", "INFO"],
    )

    assert result.exit_code == 0, result.output
    assert seen["target"].module == "app"
    assert seen["work_dir"] == str(app_dir)
    assert seen["options"] == {"url": "http://u", "no_cache": True}
    assert seen["context"] is None


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_the_run_commands_no_longer_override_the_version(app_dir, flag):
    from click.testing import CliRunner

    from arkitekt.cli.main import cli

    for command in ("dev", "prod"):
        result = CliRunner().invoke(
            cli, ["--work-dir", str(app_dir), "run", command, flag, "9.9.9"]
        )
        assert result.exit_code != 0
        assert "No such option" in result.output
