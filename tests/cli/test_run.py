"""`arkitekt run prod` and `arkitekt call remote`: the flags go to the runner, not the App.

The App is the user's declaration. The command line only decides how this run
connects, so the connection flags reach :func:`arkitekt.arun` /
:func:`arkitekt.connect` and the App is left as declared. Nothing connects:
the connection is replaced.
"""

import time
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Never

import pytest
from fakts.models import Manifest
from typer.testing import CliRunner, Result

from arkitekt import App
from arkitekt.app.options import ConnectionOptions
from arkitekt.cli.commands.app.call.remote import parse_call_args
from arkitekt.cli.main import cli_app
from arkitekt.cli.texts import MARK
from arkitekt.constants import DEFAULT_ARKITEKT_URL

from ..fakes import RecordedRun, recording_connect, write_session

#: What ``recording_connect`` records of each run: the app, and the options the
#: user passed (keyword arguments of ``connect``).
RecordedRuns = list[tuple[App[Any], dict[str, object]]]
#: The failures a test raises in a run: the error, what is said, the hint given.
Failures = list[tuple[Exception, str, str | None]]


@pytest.fixture
def recorded_runs(monkeypatch: pytest.MonkeyPatch) -> RecordedRuns:
    runs: RecordedRuns = []
    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect(runs))
    return runs


def _invoke(work_dir: Path | str, *args: str) -> Result:
    return CliRunner().invoke(cli_app, ["--work-dir", str(work_dir), *args])


def test_prod_runs_the_targets_app_with_no_flags(
    app_dir: Path, recorded_runs: RecordedRuns
) -> None:
    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code == 0, result.output
    ((app, options),) = recorded_runs
    assert (app.identifier, app.version, app.author) == (
        "com.test.app",
        "0.0.1",
        "tester",
    )
    # Unpassed flags stay unpassed: the runtime resolves them (env, defaults).
    assert options == {}


def test_prod_force_mesh_hands_the_runner_a_forced_mesh(
    app_dir: Path, recorded_runs: RecordedRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fakts.mesh import MeshOptions

    monkeypatch.delenv("ARKITEKT_MESH_PROXY", raising=False)
    result = _invoke(app_dir, "run", "prod", "app:app", "--force-mesh")

    assert result.exit_code == 0, result.output
    ((_, options),) = recorded_runs
    assert options == {"mesh": MeshOptions(force=True)}


def test_prod_reach_flags_hand_the_runner_an_alias_policy(
    app_dir: Path, recorded_runs: RecordedRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fakts.models import AliasPolicy

    monkeypatch.setenv("FAKTS_ALIAS_EXCLUDE", "old-lab")
    monkeypatch.setenv("FAKTS_ALIAS_PREFER_REACH", "public")
    result = _invoke(
        app_dir,
        "run",
        "prod",
        "app:app",
        "--prefer-reach",
        "loopback",
        "--prefer-reach",
        "lan",
        "--exclude-reach",
        "public",
    )

    assert result.exit_code == 0, result.output
    ((_, options),) = recorded_runs
    # The flags replace what the environment says of the same thing; the rest of it stays.
    assert options == {
        "alias_policy": AliasPolicy(
            prefer_reach=["loopback", "lan"],
            exclude_reach=["public"],
            exclude_aliases=["old-lab"],
        )
    }


def test_prod_hands_the_supervisor_and_device_id_to_the_runner(
    app_dir: Path, recorded_runs: RecordedRuns
) -> None:
    result = _invoke(
        app_dir,
        "run",
        "prod",
        "app:app",
        "--supervisor",
        "plugin_engine",
        "--device-id",
        "host:1",
    )

    assert result.exit_code == 0, result.output
    ((_, options),) = recorded_runs
    assert options == {"supervisor": "plugin_engine", "device_id": "host:1"}


def test_prod_hands_only_the_explicit_flags_to_the_runner(
    app_dir: Path, recorded_runs: RecordedRuns
) -> None:
    result = _invoke(
        app_dir,
        "run",
        "prod",
        "app:app",
        "--url",
        "http://fakts.example",
        "--token",
        "client:refresh",
        "--headless",
        "--log-level",
        "DEBUG",
        "--skip-cache",
        "--reauth",
    )

    assert result.exit_code == 0, result.output
    ((app, options),) = recorded_runs
    assert options == {
        "url": "http://fakts.example",
        "token": "client:refresh",
        "headless": True,
        "skip_cache": True,
        "reauth": True,
    }
    # The App is not where the connection lives, and the log level is not a
    # connection flag: it configures the process, before the run.
    for flag in ("url", "token", "headless", "log_level", "skip_cache", "reauth"):
        assert not hasattr(app, flag)


def test_prod_shows_the_apps_identity(
    app_dir: Path, recorded_runs: RecordedRuns
) -> None:
    result = _invoke(app_dir, "run", "prod")

    assert "com.test.app 0.0.1 · tester" in result.output


def test_prod_opens_with_the_mark_and_no_box(
    app_dir: Path, recorded_runs: RecordedRuns
) -> None:
    result = _invoke(app_dir, "run", "prod")

    lines = result.output.splitlines()
    for row in MARK:
        assert any(line.startswith(row) for line in lines), result.output
    assert "Arkitekt" in lines[0]
    assert "│" not in result.output and "╰" not in result.output


def test_prod_lists_what_the_app_offers(
    app_dir: Path, recorded_runs: RecordedRuns
) -> None:
    result = _invoke(app_dir, "run", "prod")

    assert "generate_n_string" in result.output


def test_prod_shows_the_default_server_when_no_url_is_passed(
    app_dir: Path, recorded_runs: RecordedRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FAKTS_URL", raising=False)

    result = _invoke(app_dir, "run", "prod")

    assert f"connecting to {DEFAULT_ARKITEKT_URL}" in result.output
    # Shown, not pinned: the runner still resolves it.
    ((_, options),) = recorded_runs
    assert options == {}


def test_prod_shows_the_server_from_the_environment(
    app_dir: Path, recorded_runs: RecordedRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKTS_URL", "http://env.example")

    result = _invoke(app_dir, "run", "prod")

    assert "connecting to http://env.example" in result.output


def test_prod_shows_the_passed_server(
    app_dir: Path, recorded_runs: RecordedRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKTS_URL", "http://env.example")

    result = _invoke(app_dir, "run", "prod", "--url", "http://fakts.example")

    assert "connecting to http://fakts.example" in result.output


def test_prod_without_an_app_module_is_a_clean_error(
    tmp_path: Path, recorded_runs: RecordedRuns
) -> None:
    result = _invoke(tmp_path, "run", "prod")

    assert result.exit_code != 0
    assert "Could not find the app module 'app'" in result.output
    assert recorded_runs == []


def test_a_crashing_run_is_reported(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def crash(run: RecordedRun) -> Never:
        raise RuntimeError("boom")

    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect([], during=crash))

    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code != 0
    assert "App crashed while running" in result.output


def test_a_run_stopped_with_ctrl_c_says_it_is_stopping(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio
    import signal

    async def interrupted(run: RecordedRun) -> None:
        signal.raise_signal(signal.SIGINT)
        await asyncio.Event().wait()

    monkeypatch.setattr(
        "arkitekt.runtime.connect", recording_connect([], during=interrupted)
    )

    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code == 0
    assert "Stopping" in result.output
    assert "Ctrl+C again to force" in result.output


def test_a_second_ctrl_c_does_not_wait_for_a_task_that_did_not_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A blocking action outlives the app in its thread; the interpreter would wait for it."""
    import io
    import threading

    from rich.console import Console

    from arkitekt.cli import running

    release = threading.Event()
    left = []
    monkeypatch.setattr(running.os, "_exit", left.append)
    out = io.StringIO()

    with running.interruptible(Console(file=out, width=200)):
        threading.Thread(target=release.wait, name="asyncio_0", daemon=True).start()
        raise KeyboardInterrupt

    release.set()
    assert left == [130]
    assert "not waiting for a task that did not stop" in out.getvalue()


def test_ctrl_c_on_a_run_with_nothing_left_behind_just_ends() -> None:
    import io

    from rich.console import Console

    from arkitekt.cli import running

    out = io.StringIO()
    with running.interruptible(Console(file=out, width=200)):
        raise KeyboardInterrupt

    assert out.getvalue() == ""


# --------------------------------------------------------------------------- #
# What a run says after the banner: its session, its connection, its failures
# --------------------------------------------------------------------------- #


def _session(logged_in_at: float) -> SimpleNamespace:
    """What a connected run's fakts holds: enough of it to be reported on."""
    auth = SimpleNamespace(chain_started_at=logged_in_at)
    this = SimpleNamespace(deployment_name="Lab")
    return SimpleNamespace(loaded_fakts=SimpleNamespace(auth=auth, self=this))


def test_a_run_on_a_saved_session_says_it_reused_it(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FAKTS_URL", raising=False)
    then = time.time() - 3 * 86400
    write_session("com.test.app", "0.0.1", DEFAULT_ARKITEKT_URL, logged_in_at=then)
    monkeypatch.setattr(
        "arkitekt.runtime.connect", recording_connect([], fakts=_session(then))
    )

    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code == 0, result.output
    assert "Session reused" in result.output and "3 days ago" in result.output


def test_a_run_that_just_logged_in_does_not_claim_a_reused_session(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The session it ends up with is newer than the one saved: it logged in again."""
    monkeypatch.delenv("FAKTS_URL", raising=False)
    write_session(
        "com.test.app", "0.0.1", DEFAULT_ARKITEKT_URL, logged_in_at=time.time() - 86400
    )
    monkeypatch.setattr(
        "arkitekt.runtime.connect", recording_connect([], fakts=_session(time.time()))
    )

    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code == 0, result.output
    assert "Session reused" not in result.output


def test_a_run_asked_to_log_in_again_never_reuses(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FAKTS_URL", raising=False)
    then = time.time() - 86400
    write_session("com.test.app", "0.0.1", DEFAULT_ARKITEKT_URL, logged_in_at=then)
    monkeypatch.setattr(
        "arkitekt.runtime.connect", recording_connect([], fakts=_session(then))
    )

    result = _invoke(app_dir, "run", "prod", "--reauth")

    assert "Session reused" not in result.output


def test_a_run_with_a_token_says_it_logged_in(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "arkitekt.runtime.connect", recording_connect([], fakts=_session(time.time()))
    )

    result = _invoke(app_dir, "run", "prod", "--token", "client:refresh")

    assert "Logged in to Lab" in result.output
    assert "client:refresh" not in result.output


def test_a_run_says_when_its_agent_is_registered_lost_and_back(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from arkitekt_spec.declare.agents.connection import ConnectionState

    async def connection(run: RecordedRun) -> None:
        assert run.listener is not None, "the CLI listens to its run"
        await run.listener(ConnectionState.REGISTERED)
        await run.listener(ConnectionState.DISCONNECTED)
        await run.listener(ConnectionState.REGISTERED)

    monkeypatch.setattr(
        "arkitekt.runtime.connect", recording_connect([], during=connection)
    )

    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code == 0, result.output
    # As one line: the first is 80 characters long, which a Windows console wraps.
    output = " ".join(result.output.split())
    assert (
        "◆ Registered providing 3 actions: append_world, generate_n_string, print_string"
        " □ Connection lost, reconnecting"
        " ◆ Reconnected"
    ) in output


def test_a_run_says_its_hub_and_when_a_mesh_path_turns_direct(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Services on one mesh host share a line; a relayed path is yellow, then direct."""
    import asyncio

    monkeypatch.setattr("arkitekt.cli.running.PATH_POLL", 0.01)
    paths = iter(["relay", "idle", "direct"])
    path = {"kind": "relay"}

    def mesh_path(key: str) -> SimpleNamespace:
        via = {"relay": "waw", "direct": "172.21.0.23:41641", "idle": None}[
            path["kind"]
        ]
        return SimpleNamespace(kind=path["kind"], via=via)

    proxy = "http://127.0.0.1:41234"
    fakts = _session(time.time())
    fakts.loaded_fakts.self.hub = "lab-hub"
    fakts.alias_map = {
        # One peer, two ports: still one line.
        "mikro": SimpleNamespace(host="lab.mesh.internal", port=8080, proxy=proxy),
        "rekuest": SimpleNamespace(host="lab.mesh.internal", port=80, proxy=proxy),
        "kabinet": SimpleNamespace(host="localhost", port=8000, proxy=None),
        # Over a proxy that cannot tell its path: never green.
        "kraph": SimpleNamespace(host="other.mesh.internal", port=None, proxy=proxy),
    }
    fakts.mesh_path = lambda key: (
        mesh_path(key) if key in ("mikro", "rekuest") else None
    )

    async def during(run: RecordedRun) -> None:
        for kind in paths:
            path["kind"] = kind
            await asyncio.sleep(0.05)

    monkeypatch.setattr(
        "arkitekt.runtime.connect", recording_connect([], fakts=fakts, during=during)
    )

    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code == 0, result.output
    output = " ".join(result.output.split())
    assert "◆ Connected to Lab hub lab-hub" in output
    assert "◆ kabinet localhost:8000" in output
    assert "■ kraph other.mesh.internal · over the mesh, path unknown" in output
    # Relayed once, idle is no news, then direct once.
    assert output.count("mikro, rekuest") == 2
    assert (
        "□ mikro, rekuest relayed lab.mesh.internal:80, 8080 · via DERP waw" in output
    )
    assert (
        "◆ mikro, rekuest direct lab.mesh.internal:80, 8080 · 172.21.0.23:41641"
        in output
    )


def test_a_run_says_which_service_is_outside_the_versions_the_app_wants(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fakts = _session(time.time())
    fakts.version_mismatches = lambda: [
        SimpleNamespace(
            key="mikro",
            service="live.arkitekt.mikro",
            running="11.4.0",
            wanted=">=12.1",
        )
    ]
    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect([], fakts=fakts))

    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code == 0, result.output
    output = " ".join(result.output.split())
    assert "□ mikro is 11.4.0 here, this app wants >=12.1 some calls may fail" in output


def _raising(
    error: Exception,
) -> Callable[..., AbstractAsyncContextManager[RecordedRun]]:
    async def during(run: RecordedRun) -> Never:
        raise error

    return recording_connect([], during=during)


def _agent_failures() -> Failures:
    errors = pytest.importorskip("rekuest.agents.transport.errors")
    return [
        (
            errors.AgentIsAlreadyBusy("busy"),
            "Another instance of this app is already connected",
            "--force",
        ),
        (
            errors.AgentWasKicked("kicked"),
            "Another instance of this app took over",
            None,
        ),
        (
            errors.DefiniteConnectionFail("Agent was kicked"),
            "Another instance of this app took over",
            None,
        ),
        (
            errors.AgentWasBlocked("blocked"),
            "The server blocked this app's agent",
            None,
        ),
        (
            errors.DefiniteConnectionFail("Exceeded Number of Retries"),
            "Lost the connection",
            None,
        ),
    ]


def _login_failures() -> Failures:
    from fakts.errors import NeedsReauthenticationError
    from fakts.grants.remote import errors

    return [
        (errors.UserDeniedError("no"), "The login was declined", None),
        (
            errors.DeviceCodeExpiredError("late"),
            "The login was not approved in time",
            None,
        ),
        (errors.DiscoveryError("nowhere"), "Could not reach the server", "--url"),
        (
            NeedsReauthenticationError("idle"),
            "The session is no longer valid",
            "arkitekt login --reauth",
        ),
    ]


@pytest.mark.parametrize("failures", [_agent_failures, _login_failures])
@pytest.mark.parametrize("command", ["prod"])
def test_a_failure_the_user_can_act_on_is_one_line(
    app_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    failures: Callable[[], Failures],
    command: str,
) -> None:
    for error, message, hint in failures():
        monkeypatch.setattr("arkitekt.runtime.connect", _raising(error))

        result = _invoke(app_dir, "run", command)

        flat = " ".join(result.output.split())
        assert result.exit_code == 1, result.output
        assert message in flat, result.output
        assert hint is None or hint in flat
        assert "Traceback" not in result.output and "App crashed" not in result.output


def test_an_unknown_transport_failure_keeps_its_traceback(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    errors = pytest.importorskip("rekuest.agents.transport.errors")
    monkeypatch.setattr(
        "arkitekt.runtime.connect",
        _raising(errors.DefiniteConnectionFail(ValueError("odd"))),
    )

    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code != 0
    assert "App crashed while running" in result.output


# --------------------------------------------------------------------------- #
# call remote
# --------------------------------------------------------------------------- #


def test_call_args_are_read_as_json_when_they_parse() -> None:
    assert parse_call_args(["n=3", "name=bob", "flags=[1, 2]", 'quoted="7"']) == {
        "n": 3,
        "name": "bob",
        "flags": [1, 2],
        "quoted": "7",
    }
    with pytest.raises(ValueError, match="key=value"):
        parse_call_args(["novalue"])


def test_call_remote_connects_the_app_and_calls_through_its_rekuest(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from rekuest.client.client import RekuestCaller

    seen = {}

    class FakeRekuest:
        async def afind(self, hash: str) -> str:
            seen["hash"] = hash
            return "the-action"

        async def acall_raw(
            self, kwargs: dict[str, int], action: str
        ) -> dict[str, int]:
            seen["call"] = (kwargs, action)
            return {"returned": kwargs["n"] + 1}

    class FakeRuntime:
        def require(self, cls: type) -> FakeRekuest:
            assert cls is RekuestCaller
            return FakeRekuest()

    @asynccontextmanager
    async def fake_connect(
        app: App[Any], **options: object
    ) -> AsyncIterator[FakeRuntime]:
        seen["app"], seen["options"] = app, options
        yield FakeRuntime()

    monkeypatch.setattr("arkitekt.runtime.connect", fake_connect)

    result = _invoke(
        app_dir, "call", "remote", "ab" * 32, "app", "-a", "n=41", "--url", "http://u"
    )

    assert result.exit_code == 0, result.output
    # Whatever is called, the caller is the CLI's own app.
    assert seen["app"].identifier == "arkitekt-cli"
    assert seen["options"] == {"url": "http://u"}
    assert seen["hash"] == "ab" * 32
    assert seen["call"] == ({"n": 41}, "the-action")
    assert '"returned": 42' in result.output


def test_call_remote_with_an_agent_calls_the_action_on_that_agent(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = {}

    class FakeRekuest:
        async def afind(self, hash: str) -> str:
            return "the-action"

        async def acall_raw(
            self, kwargs: dict[str, object], action: str, on_agent: str
        ) -> None:
            seen["call"] = (action, on_agent)

    class FakeRuntime:
        def require(self, cls: type) -> FakeRekuest:
            return FakeRekuest()

    @asynccontextmanager
    async def fake_connect(
        app: App[Any], **options: object
    ) -> AsyncIterator[FakeRuntime]:
        seen["options"] = options
        yield FakeRuntime()

    monkeypatch.setattr("arkitekt.runtime.connect", fake_connect)

    result = _invoke(app_dir, "call", "remote", "ab" * 32, "--agent", "7")

    assert result.exit_code == 0, result.output
    assert seen["call"] == ("the-action", "7")
    # The agent is the call's, not the connection's.
    assert seen["options"] == {}


def test_call_remote_without_an_app_calls_as_the_cli_app_with_rekuest(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("rekuest")
    monkeypatch.delenv("ARKITEKT_APP", raising=False)
    seen = {}

    class FakeRekuest:
        async def afind(self, hash: str) -> str:
            return "the-action"

        async def acall_raw(self, kwargs: dict[str, object], action: str) -> str:
            return "ok"

    class FakeRuntime:
        def require(self, cls: type) -> FakeRekuest:
            return FakeRekuest()

    @asynccontextmanager
    async def fake_connect(
        app: App[Any], **options: object
    ) -> AsyncIterator[FakeRuntime]:
        seen["app"] = app
        yield FakeRuntime()

    monkeypatch.setattr("arkitekt.runtime.connect", fake_connect)

    result = _invoke(app_dir, "call", "remote", "ab" * 32)

    assert result.exit_code == 0, result.output
    assert seen["app"].identifier == "arkitekt-cli"
    assert "rekuest_caller" in seen["app"].registry.clients


def test_the_cli_app_uses_rekuest_and_offers_nothing() -> None:
    pytest.importorskip("rekuest")
    from rekuest.client.client import RekuestCaller

    from arkitekt import runtime
    from arkitekt.cli.commands.app.call.remote import cli_app as make_cli_app

    app = make_cli_app()

    # It starts tasks as roots: the caller, a rekuest client of its own.
    assert app.clients() == [RekuestCaller]
    assert list(app.registry.clients) == ["rekuest_caller"]
    assert app.is_empty()
    # call remote only connects: no agent is built, so nothing is provided.
    assert runtime.connect(app).provider is None


def test_call_remote_needs_an_action(app_dir: Path) -> None:
    result = _invoke(app_dir, "call", "remote")

    assert result.exit_code != 0
    assert "ACTION" in result.output.upper()


def test_call_remote_finds_one_of_the_apps_actions_by_its_name(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The name becomes the hash of the definition, which is what the server knows it by."""
    pytest.importorskip("rekuest")
    from arkitekt_spec import definition_hash

    from arkitekt.cli.target import load_target

    seen = {}

    class FakeRekuest:
        async def afind(self, hash: str) -> str:
            seen["hash"] = hash
            return "the-action"

        async def acall_raw(self, kwargs: dict[str, object], action: str) -> str:
            return "ok"

    class FakeRuntime:
        def require(self, cls: type) -> FakeRekuest:
            return FakeRekuest()

    @asynccontextmanager
    async def fake_connect(
        app: App[Any], **options: object
    ) -> AsyncIterator[FakeRuntime]:
        seen["app"] = app
        yield FakeRuntime()

    monkeypatch.setattr("arkitekt.runtime.connect", fake_connect)

    result = _invoke(app_dir, "call", "remote", "append_world", "-a", "hello=hi")

    assert result.exit_code == 0, result.output
    # The app in the folder names the action; it is not who calls.
    assert seen["app"].identifier == "arkitekt-cli"
    app, _, _ = load_target("app", str(app_dir))
    assert seen["hash"] == definition_hash(
        app.registry.implementations["append_world"].definition
    )


# ---------------------------------------------------------------------------
# call local: the app's own action, in this process
# ---------------------------------------------------------------------------


def test_call_local_runs_the_action_here_and_prints_its_result(app_dir: Path) -> None:
    result = _invoke(app_dir, "call", "local", "append_world", "-a", "hello=hi")

    assert result.exit_code == 0, result.output
    assert "hi World" in result.output


def test_call_local_logs_in_to_nothing_for_an_app_without_clients(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def never(manifest: Manifest, options: ConnectionOptions) -> Never:
        raise AssertionError("a local call of an app without clients built a fakts")

    monkeypatch.setattr("arkitekt.runtime.build_fakts", never)

    result = _invoke(
        app_dir, "call", "local", "append_world", "-a", "hello=hi", "--online"
    )

    assert result.exit_code == 0, result.output


def test_call_local_refuses_a_connection_flag_without_online(app_dir: Path) -> None:
    result = _invoke(
        app_dir, "call", "local", "append_world", "-a", "hello=hi", "--reauth"
    )

    assert result.exit_code != 0
    assert "--reauth" in result.output
    assert "--online" in result.output


def test_call_local_ignores_a_connection_the_environment_names(
    app_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exported FAKTS_URL is for the commands that connect."""
    monkeypatch.setenv("FAKTS_URL", "http://somewhere.invalid")

    result = _invoke(app_dir, "call", "local", "append_world", "-a", "hello=hi")

    assert result.exit_code == 0, result.output
    assert "hi World" in result.output


def test_call_local_prints_each_result_of_a_generator(app_dir: Path) -> None:
    result = _invoke(
        app_dir, "call", "local", "generate_n_string", "-a", "n=2", "-a", "timeout=0"
    )

    assert result.exit_code == 0, result.output
    assert '"Hello 0"' in result.output
    assert '"Hello 1"' in result.output


def test_call_local_of_an_unknown_action_lists_the_apps_actions(app_dir: Path) -> None:
    result = _invoke(app_dir, "call", "local", "nope")

    assert result.exit_code != 0
    assert "has no action 'nope'" in result.output
    assert "append_world" in result.output


@pytest.mark.parametrize(
    ("args", "said"),
    [
        ([], "needs hello"),
        (["-a", "hello=hi", "-a", "other=1"], "takes no argument other"),
    ],
)
def test_call_local_says_what_the_action_takes(
    app_dir: Path, args: list[str], said: str
) -> None:
    result = _invoke(app_dir, "call", "local", "append_world", *args)

    assert result.exit_code != 0
    assert said in result.output
    assert "hello (STRING)" in result.output


def test_call_local_of_a_raising_action_fails_in_one_line(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        "from arkitekt import App\n"
        "app = App('boom', '0.1.0')\n"
        "@app.action\n"
        "def boom() -> str:\n"
        "    'Boom'\n"
        "    raise ValueError('nope')\n"
    )

    result = _invoke(tmp_path, "call", "local", "boom")

    assert result.exit_code == 1
    assert "boom failed" in result.output
    assert "nope" in result.output


def test_inspect_implementations_lists_what_to_call(app_dir: Path) -> None:
    result = _invoke(app_dir, "inspect", "implementations")

    assert result.exit_code == 0, result.output
    assert "append_world" in result.output
    assert "hello: STRING" in result.output


def test_call_remote_of_what_is_neither_a_name_nor_a_hash_lists_the_apps_actions(
    app_dir: Path,
) -> None:
    result = _invoke(app_dir, "call", "remote", "apend_world")

    assert result.exit_code != 0
    assert "neither an action" in result.output
    assert "append_world" in result.output
