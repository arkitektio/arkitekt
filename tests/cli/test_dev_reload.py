"""What `arkitekt run dev` reloads when code changes, and what it runs then.

A change is loaded beside the app that is running and checked before it replaces
it: the project's modules are imported anew (so a change in a helper reaches the
module that imported it), the App they declare is validated, and only then is
the old run stopped. A save that does not load changes nothing.
"""

import asyncio
import io
import signal
import sys

import pytest

from arkitekt.cli.commands.app.run import dev as dev_module
from arkitekt.cli.commands.app.run.dev import (
    Candidate,
    _start,
    concerns,
    development_modules,
    development_roots,
    load_candidate,
    project_modules,
    run_dev,
)
from arkitekt.cli.running import TaskReporter
from arkitekt.cli.target import parse_target
from arkitekt_spec.declare.agents.connection import TaskEvent, TaskEventKind
from rich.console import Console

from ..fakes import recording_connect


def _declare(path, identifier: str, helper: str = "") -> None:
    path.write_text(
        "from arkitekt import App\n"
        + (f"import {helper}\n" if helper else "")
        + f"app = App({identifier!r})\n\n"
        "@app.action\n"
        "def f(x: int) -> int:\n"
        + (f"    return x + {helper}.OFFSET\n" if helper else "    return x\n")
    )


@pytest.fixture()
def project(tmp_path, monkeypatch):
    """A work dir on the path, whose modules are forgotten again afterwards."""
    monkeypatch.syspath_prepend(str(tmp_path))
    before = set(sys.modules)
    yield tmp_path
    for name in set(sys.modules) - before:
        if getattr(sys.modules[name], "__file__", None) and str(tmp_path) in sys.modules[name].__file__:
            del sys.modules[name]


def test_a_reload_runs_the_new_app_with_the_same_connection_flags(project, monkeypatch):
    """The App is looked up again after a reload; the flags go to the runner each time."""
    runs = []
    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect(runs))
    entry = project / "devreloaded.py"
    _declare(entry, "before")
    target = parse_target("devreloaded", str(project))
    console = Console(file=io.StringIO())

    async def scenario():
        await _start(console, load_candidate(target, []), {"url": "http://x"})
        # A different length, so the bytecode cache cannot mistake it for the old file.
        _declare(entry, "after the change")
        await _start(console, load_candidate(target, project_modules(str(project))), {"url": "http://x"})

    asyncio.run(scenario())

    assert [app.identifier for app, _ in runs] == ["before", "after the change"]
    assert runs[0][0] is not runs[1][0]
    assert all(options == {"url": "http://x"} for _, options in runs)


def test_a_change_in_a_helper_reaches_the_app_that_imports_it(project):
    (project / "devhelper.py").write_text("OFFSET = 1\n")
    _declare(project / "devwithhelper.py", "helped", helper="devhelper")
    target = parse_target("devwithhelper", str(project))

    first = load_candidate(target, [])
    assert first.module.f(1) == 2
    assert {"devhelper", "devwithhelper"} <= set(project_modules(str(project)))

    (project / "devhelper.py").write_text("OFFSET = 100  # changed\n")
    second = load_candidate(target, project_modules(str(project)))

    assert second.module.f(1) == 101
    assert first.module.f(1) == 2, "the code that was running keeps the modules it had"


@pytest.mark.parametrize(
    ("broken", "said"),
    [
        ("from arkitekt import App\napp = App('x'\n", "never closed"),
        ("from arkitekt import App\napp = App('x')\n@app.action\ndef f(x) -> int:\n    return 1\n", "type hint"),
        ("import nothing_of_that_name\n", "nothing_of_that_name"),
        ("x = 1\n", "App"),
    ],
)
def test_a_change_that_does_not_load_leaves_everything_as_it_was(project, broken, said):
    entry = project / "devbroken.py"
    _declare(entry, "working")
    target = parse_target("devbroken", str(project))
    working = load_candidate(target, [])

    entry.write_text(broken)
    with pytest.raises(Exception, match=said):
        load_candidate(target, project_modules(str(project)))

    assert sys.modules["devbroken"] is working.module


def test_the_project_is_what_lives_in_the_folder_outside_an_environment(project):
    (project / ".venv" / "lib").mkdir(parents=True)
    (project / ".venv" / "lib" / "devvendored.py").write_text("X = 1\n")
    (project / "devmine.py").write_text("X = 1\n")
    sys.path.insert(0, str(project / ".venv" / "lib"))
    try:
        import devmine  # noqa: F401
        import devvendored  # noqa: F401

        mine = project_modules(str(project))
    finally:
        sys.path.remove(str(project / ".venv" / "lib"))
        sys.modules.pop("devvendored", None)

    assert "devmine" in mine
    assert "devvendored" not in mine
    assert "pytest" not in mine


def test_deep_follows_packages_that_live_outside_the_project_and_any_environment(project, tmp_path_factory):
    elsewhere = tmp_path_factory.mktemp("checkout")
    (elsewhere / "devlinked").mkdir()
    (elsewhere / "devlinked" / "__init__.py").write_text("X = 1\n")
    sys.path.insert(0, str(elsewhere))
    baseline = frozenset(sys.modules)
    try:
        import devlinked  # noqa: F401

        roots = development_roots(str(project), baseline)
        modules = development_modules(str(project), baseline)
    finally:
        sys.path.remove(str(elsewhere))
        sys.modules.pop("devlinked", None)

    assert roots == [str(elsewhere / "devlinked")]
    assert modules == ["devlinked"]


def test_what_was_loaded_before_the_app_is_never_reloaded(project):
    """The SDK the CLI runs on may live in the folder, or be a checkout: it is not the app's."""
    (project / "devsdk.py").write_text("X = 1\n")
    import devsdk  # noqa: F401

    baseline = frozenset(sys.modules)
    (project / "devappmodule.py").write_text("X = 1\n")
    import devappmodule  # noqa: F401

    assert project_modules(str(project), baseline) == ["devappmodule"]
    # arkitekt itself is a checkout outside any environment here, and stays put.
    assert "arkitekt" not in development_modules(str(project), baseline)


def test_only_a_change_to_what_the_app_is_made_of_concerns_it(project):
    made_of = {str(project / "app.py"), str(project / "helper.py")}

    assert concerns({(1, str(project / "helper.py"))}, made_of)
    assert not concerns({(1, str(project / "another_script.py"))}, made_of)
    # An app that did not load is made of nothing known: any change may be the fix.
    assert concerns({(1, str(project / "another_script.py"))}, None)


def _watching(*bursts, changed):
    """A stand-in for watchfiles' ``awatch``: runs each burst's ``before``, then yields a
    change to each of the ``changed`` files."""

    async def awatch(*roots, **options):
        for before in bursts:
            await asyncio.sleep(0.01)  # the run that was started gets to run
            before()
            yield {(1, str(path)) for path in changed}

    return awatch


def test_a_broken_save_keeps_the_last_working_version_running(project, monkeypatch):
    runs = []
    stopped = []

    async def forever(run):
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            stopped.append(run.app.identifier)
            raise

    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect(runs, during=forever))
    entry = project / "devkept.py"
    _declare(entry, "first")
    target = parse_target("devkept", str(project))
    out = io.StringIO()

    def break_it():
        assert [app.identifier for app, _ in runs] == ["first"]
        entry.write_text("from arkitekt import App\napp = App('second'\n")

    def fix_it():
        # The broken save neither stopped the first run nor started another.
        assert [app.identifier for app, _ in runs] == ["first"]
        assert stopped == []
        _declare(entry, "third, fixed")

    monkeypatch.setattr(dev_module, "awatch", _watching(break_it, fix_it, changed=[entry]))

    async def scenario():
        await run_dev(Console(file=out, width=200), target, str(project))
        await asyncio.sleep(0.01)
        for task in asyncio.all_tasks() - {asyncio.current_task()}:
            task.cancel()

    asyncio.run(scenario())

    assert [app.identifier for app, _ in runs] == ["first", "third, fixed"]
    assert stopped[0] == "first"
    said = out.getvalue()
    assert "SyntaxError" in said
    assert "still running the last working version" in said
    assert "Traceback" not in said


def test_ctrl_c_stops_the_app_before_the_dev_run_ends(project, monkeypatch):
    """The dev loop stops its app itself, and says so: nothing is left to the closing loop."""
    events = []

    async def forever(run):
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            events.append("app stopped")
            raise

    async def awatch(*roots, **options):
        await asyncio.sleep(0.01)  # the run that was started gets to run
        signal.raise_signal(signal.SIGINT)
        await asyncio.Event().wait()
        yield set()

    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect([], during=forever))
    monkeypatch.setattr(dev_module, "awatch", awatch)
    _declare(project / "devstopped.py", "stopped")
    target = parse_target("devstopped", str(project))
    out = io.StringIO()

    async def scenario():
        try:
            await run_dev(Console(file=out, width=200), target, str(project))
        finally:
            events.append("dev run ended")

    with pytest.raises(KeyboardInterrupt):
        asyncio.run(scenario())

    assert events == ["app stopped", "dev run ended"]
    assert "Ctrl+C again to force" in out.getvalue()


def test_an_app_that_never_loaded_starts_once_it_does(project, monkeypatch):
    runs = []
    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect(runs))
    entry = project / "devlate.py"
    entry.write_text("this is not python\n")
    target = parse_target("devlate", str(project))
    out = io.StringIO()
    monkeypatch.setattr(
        dev_module, "awatch", _watching(lambda: _declare(entry, "at last"), changed=[entry])
    )

    async def scenario():
        await run_dev(Console(file=out, width=200), target, str(project))
        await asyncio.sleep(0.01)

    asyncio.run(scenario())

    assert [app.identifier for app, _ in runs] == ["at last"]
    assert "The app does not load" in out.getvalue()


def test_the_dev_run_reports_its_tasks_and_a_plain_run_does_not(project, monkeypatch):
    seen = []

    async def note(run):
        seen.append(run.task_listener)

    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect([], during=note))
    _declare(project / "devtasks.py", "tasks")
    target = parse_target("devtasks", str(project))
    console = Console(file=io.StringIO())

    async def scenario():
        from arkitekt.cli.running import arun_app

        candidate = load_candidate(target, [])
        await _start(console, candidate, {})
        await arun_app(console, candidate.app, {})

    asyncio.run(scenario())

    assert isinstance(seen[0], TaskReporter)
    assert seen[1] is None


def test_a_task_is_one_line_when_it_arrives_and_one_when_it_ends():
    out = io.StringIO()
    reporter = TaskReporter(Console(file=out, width=200))

    async def scenario():
        await reporter(TaskEvent("t1", "add", TaskEventKind.ASSIGNED, arguments={"a": 1, "b": "x" * 80}))
        await reporter(TaskEvent("t1", "add", TaskEventKind.PROGRESS, progress=50))
        await reporter(TaskEvent("t1", "add", TaskEventKind.DONE))
        await reporter(TaskEvent("t2", "boom", TaskEventKind.ASSIGNED))
        await reporter(TaskEvent("t2", "boom", TaskEventKind.FAILED, error="nope [really]"))

    asyncio.run(scenario())

    lines = out.getvalue().splitlines()
    assert len(lines) == 4
    assert "add" in lines[0] and "a=1" in lines[0] and "…" in lines[0]
    assert "add" in lines[1] and "ms" in lines[1]
    assert "boom failed" in lines[3] and "nope [really]" in lines[3]


def test_a_failure_the_user_can_act_on_is_one_line_in_the_dev_loop(project, monkeypatch):
    errors = pytest.importorskip("rekuest.agents.transport.errors")

    async def busy(run):
        raise errors.AgentIsAlreadyBusy("busy")

    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect([], during=busy))
    _declare(project / "devbusy.py", "busy-app")
    target = parse_target("devbusy", str(project))
    out = io.StringIO()
    console = Console(file=out, width=200)

    async def scenario():
        run = _start(console, load_candidate(target, []), {})
        await asyncio.wait([run])
        await asyncio.sleep(0)  # the done-callback reports

    asyncio.run(scenario())

    assert "Another instance of this app is already connected" in out.getvalue()
    assert "--force" in out.getvalue()
    assert "Traceback" not in out.getvalue()


def test_a_candidate_is_the_module_its_app_and_its_context(project):
    _declare(project / "devcandidate.py", "candidate")
    candidate = load_candidate(parse_target("devcandidate", str(project)), [])

    assert isinstance(candidate, Candidate)
    assert candidate.app.identifier == "candidate"
    assert candidate.context is None


def test_dev_hands_the_explicit_flags_to_the_loop(app_dir, monkeypatch):
    from typer.testing import CliRunner

    from arkitekt.cli.main import cli_app

    seen = {}

    async def fake_run_dev(console, target, work_dir, options=None, deep=False, context=None, context_file=None):
        seen.update(target=target, work_dir=work_dir, options=options, deep=deep, context=context)

    monkeypatch.setattr(dev_module, "run_dev", fake_run_dev)

    result = CliRunner().invoke(
        cli_app,
        ["--work-dir", str(app_dir), "run", "dev", "app.py", "--url", "http://u", "--reauth", "-l", "INFO"],
    )

    assert result.exit_code == 0, result.output
    assert seen["target"].module == "app"
    assert seen["work_dir"] == str(app_dir)
    assert seen["options"] == {"url": "http://u", "reauth": True}
    assert seen["context"] is None


def test_dev_force_mesh_reaches_the_runner_as_the_mesh_it_stands_for(app_dir, monkeypatch):
    """--force-mesh is no connection keyword of its own: the runner gets the
    mesh configuration it means -- a node of our own, or the proxy the
    environment names -- with nothing else to fall back to."""
    from fakts.mesh import MeshOptions, MeshProxy
    from typer.testing import CliRunner

    from arkitekt.cli.main import cli_app

    seen = {}

    async def fake_run_dev(console, target, work_dir, options=None, **kwargs):
        seen.update(options=options)

    monkeypatch.setattr(dev_module, "run_dev", fake_run_dev)
    monkeypatch.delenv("ARKITEKT_MESH_PROXY", raising=False)

    def run_dev(*flags: str) -> dict:
        result = CliRunner().invoke(
            cli_app, ["--work-dir", str(app_dir), "run", "dev", "app.py", *flags]
        )
        assert result.exit_code == 0, result.output
        return seen["options"]

    assert run_dev() == {}, "unpassed, the mesh is the runtime's to decide"
    assert run_dev("--force-mesh") == {"mesh": MeshOptions(force=True)}
    monkeypatch.setenv("ARKITEKT_MESH_PROXY", "http://localhost:1055")
    assert run_dev("--force-mesh") == {
        "mesh": MeshProxy(url="http://localhost:1055", force=True)
    }


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_the_run_commands_no_longer_override_the_version(app_dir, flag):
    from typer.testing import CliRunner

    from arkitekt.cli.main import cli_app

    for command in ("dev", "prod"):
        result = CliRunner().invoke(
            cli_app, ["--work-dir", str(app_dir), "run", command, flag, "9.9.9"]
        )
        assert result.exit_code != 0
        assert "No such option" in result.output


def test_a_save_to_a_file_the_app_does_not_import_restarts_nothing(project, monkeypatch):
    runs = []

    async def forever(run):
        await asyncio.Event().wait()

    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect(runs, during=forever))
    _declare(project / "devfocused.py", "focused")
    other = project / "devunrelated.py"
    other.write_text("X = 1\n")
    target = parse_target("devfocused", str(project))
    out = io.StringIO()
    monkeypatch.setattr(
        dev_module, "awatch", _watching(lambda: other.write_text("X = 2\n"), changed=[other])
    )

    async def scenario():
        await run_dev(Console(file=out, width=200), target, str(project))
        await asyncio.sleep(0.01)
        for task in asyncio.all_tasks() - {asyncio.current_task()}:
            task.cancel()

    asyncio.run(scenario())

    assert [app.identifier for app, _ in runs] == ["focused"]
    assert "devunrelated" not in out.getvalue()
