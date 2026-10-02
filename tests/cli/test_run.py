"""`arkitekt run prod` and `arkitekt call remote`: the flags go to the runner, not the App.

The App is the user's declaration. The command line only decides how this run
connects, so the connection flags reach :func:`arkitekt.arun` /
:func:`arkitekt.connect` and the App is left as declared. Nothing connects:
the connection is replaced.
"""

import time
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from arkitekt.cli.commands.app.call.remote import parse_call_args
from arkitekt.cli.main import cli_app
from arkitekt.cli.texts import MARK
from arkitekt.constants import DEFAULT_ARKITEKT_URL

from ..fakes import recording_connect, write_session


@pytest.fixture
def recorded_runs(monkeypatch):
    runs = []
    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect(runs))
    return runs


def _invoke(work_dir, *args):
    return CliRunner().invoke(cli_app, ["--work-dir", str(work_dir), *args])


def test_prod_runs_the_targets_app_with_no_flags(app_dir, recorded_runs):
    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code == 0, result.output
    ((app, options),) = recorded_runs
    assert (app.identifier, app.version, app.author) == ("com.test.app", "0.0.1", "tester")
    # Unpassed flags stay unpassed: the runtime resolves them (env, defaults).
    assert options == {}


def test_prod_hands_only_the_explicit_flags_to_the_runner(app_dir, recorded_runs):
    result = _invoke(
        app_dir, "run", "prod", "app:app",
        "--url", "http://fakts.example",
        "--token", "client:refresh",
        "--headless",
        "--log-level", "DEBUG",
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


def test_prod_shows_the_apps_identity(app_dir, recorded_runs):
    result = _invoke(app_dir, "run", "prod")

    assert "com.test.app 0.0.1 · tester" in result.output


def test_prod_opens_with_the_mark_and_no_box(app_dir, recorded_runs):
    result = _invoke(app_dir, "run", "prod")

    lines = result.output.splitlines()
    for row in MARK:
        assert any(line.startswith(row) for line in lines), result.output
    assert "Arkitekt" in lines[0]
    assert "│" not in result.output and "╰" not in result.output


def test_prod_lists_what_the_app_offers(app_dir, recorded_runs):
    result = _invoke(app_dir, "run", "prod")

    assert "generate_n_string" in result.output


def test_prod_shows_the_default_server_when_no_url_is_passed(
    app_dir, recorded_runs, monkeypatch
):
    monkeypatch.delenv("FAKTS_URL", raising=False)

    result = _invoke(app_dir, "run", "prod")

    assert f"connecting to {DEFAULT_ARKITEKT_URL}" in result.output
    # Shown, not pinned: the runner still resolves it.
    ((_, options),) = recorded_runs
    assert options == {}


def test_prod_shows_the_server_from_the_environment(app_dir, recorded_runs, monkeypatch):
    monkeypatch.setenv("FAKTS_URL", "http://env.example")

    result = _invoke(app_dir, "run", "prod")

    assert "connecting to http://env.example" in result.output


def test_prod_shows_the_passed_server(app_dir, recorded_runs, monkeypatch):
    monkeypatch.setenv("FAKTS_URL", "http://env.example")

    result = _invoke(app_dir, "run", "prod", "--url", "http://fakts.example")

    assert "connecting to http://fakts.example" in result.output


def test_prod_without_an_app_module_is_a_clean_error(tmp_path, recorded_runs):
    result = _invoke(tmp_path, "run", "prod")

    assert result.exit_code != 0
    assert "Could not find the app module 'app'" in result.output
    assert recorded_runs == []


def test_a_crashing_run_is_reported(app_dir, monkeypatch):
    async def crash(run):
        raise RuntimeError("boom")

    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect([], during=crash))

    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code != 0
    assert "App crashed while running" in result.output


# --------------------------------------------------------------------------- #
# What a run says after the banner: its session, its connection, its failures
# --------------------------------------------------------------------------- #


def _session(logged_in_at):
    """What a connected run's fakts holds: enough of it to be reported on."""
    auth = SimpleNamespace(chain_started_at=logged_in_at)
    this = SimpleNamespace(deployment_name="Lab")
    return SimpleNamespace(loaded_fakts=SimpleNamespace(auth=auth, self=this))


def test_a_run_on_a_saved_session_says_it_reused_it(app_dir, monkeypatch):
    monkeypatch.delenv("FAKTS_URL", raising=False)
    then = time.time() - 3 * 86400
    write_session("com.test.app", "0.0.1", DEFAULT_ARKITEKT_URL, logged_in_at=then)
    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect([], fakts=_session(then)))

    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code == 0, result.output
    assert "Session reused" in result.output and "3 days ago" in result.output


def test_a_run_that_just_logged_in_does_not_claim_a_reused_session(app_dir, monkeypatch):
    """The session it ends up with is newer than the one saved: it logged in again."""
    monkeypatch.delenv("FAKTS_URL", raising=False)
    write_session("com.test.app", "0.0.1", DEFAULT_ARKITEKT_URL, logged_in_at=time.time() - 86400)
    monkeypatch.setattr(
        "arkitekt.runtime.connect", recording_connect([], fakts=_session(time.time()))
    )

    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code == 0, result.output
    assert "Session reused" not in result.output


def test_a_run_asked_to_log_in_again_never_reuses(app_dir, monkeypatch):
    monkeypatch.delenv("FAKTS_URL", raising=False)
    then = time.time() - 86400
    write_session("com.test.app", "0.0.1", DEFAULT_ARKITEKT_URL, logged_in_at=then)
    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect([], fakts=_session(then)))

    result = _invoke(app_dir, "run", "prod", "--reauth")

    assert "Session reused" not in result.output


def test_a_run_with_a_token_says_it_logged_in(app_dir, monkeypatch):
    monkeypatch.setattr(
        "arkitekt.runtime.connect", recording_connect([], fakts=_session(time.time()))
    )

    result = _invoke(app_dir, "run", "prod", "--token", "client:refresh")

    assert "Logged in to Lab" in result.output
    assert "client:refresh" not in result.output


def test_a_run_says_when_its_agent_is_registered_lost_and_back(app_dir, monkeypatch):
    from arkitekt_runtime.agents.connection import ConnectionState

    async def connection(run):
        await run.listener(ConnectionState.REGISTERED)
        await run.listener(ConnectionState.DISCONNECTED)
        await run.listener(ConnectionState.REGISTERED)

    monkeypatch.setattr("arkitekt.runtime.connect", recording_connect([], during=connection))

    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code == 0, result.output
    lines = [line.strip() for line in result.output.splitlines()]
    registered = lines.index("◆ Registered  providing 3 actions")
    assert lines[registered + 1 : registered + 3] == [
        "□ Connection lost, reconnecting",
        "◆ Reconnected",
    ]


def _raising(error):
    async def during(run):
        raise error

    return recording_connect([], during=during)


def _agent_failures():
    errors = pytest.importorskip("rekuest.agents.transport.errors")
    return [
        (errors.AgentIsAlreadyBusy("busy"), "Another instance of this app is already connected", "--force"),
        (errors.AgentWasKicked("kicked"), "Another instance of this app took over", None),
        (errors.DefiniteConnectionFail("Agent was kicked"), "Another instance of this app took over", None),
        (errors.AgentWasBlocked("blocked"), "The server blocked this app's agent", None),
        (errors.DefiniteConnectionFail("Exceeded Number of Retries"), "Lost the connection", None),
    ]


def _login_failures():
    from fakts.errors import NeedsReauthenticationError
    from fakts.grants.remote import errors

    return [
        (errors.UserDeniedError("no"), "The login was declined", None),
        (errors.DeviceCodeExpiredError("late"), "The login was not approved in time", None),
        (errors.DiscoveryError("nowhere"), "Could not reach the server", "--url"),
        (NeedsReauthenticationError("idle"), "The session is no longer valid", "arkitekt login --reauth"),
    ]


@pytest.mark.parametrize("failures", [_agent_failures, _login_failures])
@pytest.mark.parametrize("command", ["prod"])
def test_a_failure_the_user_can_act_on_is_one_line(app_dir, monkeypatch, failures, command):
    for error, message, hint in failures():
        monkeypatch.setattr("arkitekt.runtime.connect", _raising(error))

        result = _invoke(app_dir, "run", command)

        flat = " ".join(result.output.split())
        assert result.exit_code == 1, result.output
        assert message in flat, result.output
        assert hint is None or hint in flat
        assert "Traceback" not in result.output and "App crashed" not in result.output


def test_an_unknown_transport_failure_keeps_its_traceback(app_dir, monkeypatch):
    errors = pytest.importorskip("rekuest.agents.transport.errors")
    monkeypatch.setattr(
        "arkitekt.runtime.connect", _raising(errors.DefiniteConnectionFail(ValueError("odd")))
    )

    result = _invoke(app_dir, "run", "prod")

    assert result.exit_code != 0
    assert "App crashed while running" in result.output


# --------------------------------------------------------------------------- #
# call remote
# --------------------------------------------------------------------------- #


def test_call_args_are_read_as_json_when_they_parse():
    assert parse_call_args(["n=3", "name=bob", "flags=[1, 2]", 'quoted="7"']) == {
        "n": 3,
        "name": "bob",
        "flags": [1, 2],
        "quoted": "7",
    }
    with pytest.raises(ValueError, match="key=value"):
        parse_call_args(["novalue"])


def test_call_remote_connects_the_app_and_calls_through_its_rekuest(app_dir, monkeypatch):
    from rekuest.client.client import Rekuest

    seen = {}

    class FakeRekuest:
        async def afind(self, hash):
            seen["hash"] = hash
            return "the-action"

        async def acall_raw(self, kwargs, action):
            seen["call"] = (kwargs, action)
            return {"returned": kwargs["n"] + 1}

    class FakeRuntime:
        def get(self, cls):
            assert cls is Rekuest
            return FakeRekuest()

    @asynccontextmanager
    async def fake_connect(app, **options):
        seen["app"], seen["options"] = app, options
        yield FakeRuntime()

    monkeypatch.setattr("arkitekt.runtime.connect", fake_connect)

    result = _invoke(
        app_dir, "call", "remote", "app", "--hash", "abc", "-a", "n=41", "--url", "http://u"
    )

    assert result.exit_code == 0, result.output
    assert seen["app"].identifier == "com.test.app"
    assert seen["options"] == {"url": "http://u"}
    assert seen["hash"] == "abc"
    assert seen["call"] == ({"n": 41}, "the-action")
    assert '"returned": 42' in result.output


def test_call_remote_without_an_app_calls_as_the_cli_app_with_rekuest(
    app_dir, monkeypatch
):
    pytest.importorskip("rekuest")
    monkeypatch.delenv("ARKITEKT_APP", raising=False)
    seen = {}

    class FakeRekuest:
        async def afind(self, hash):
            return "the-action"

        async def acall_raw(self, kwargs, action):
            return "ok"

    class FakeRuntime:
        def get(self, cls):
            return FakeRekuest()

    @asynccontextmanager
    async def fake_connect(app, **options):
        seen["app"] = app
        yield FakeRuntime()

    monkeypatch.setattr("arkitekt.runtime.connect", fake_connect)

    result = _invoke(app_dir, "call", "remote", "--hash", "abc")

    assert result.exit_code == 0, result.output
    assert seen["app"].identifier == "arkitekt-cli"
    assert "rekuest" in seen["app"].services


def test_the_cli_app_uses_rekuest_and_offers_nothing():
    pytest.importorskip("rekuest")
    from arkitekt import runtime
    from arkitekt.cli.commands.app.call.remote import cli_app as make_cli_app

    app = make_cli_app()

    assert app.services == ["rekuest"]
    assert app.registry.is_empty()
    # call remote only connects: no agent is built, so nothing is provided.
    assert runtime.connect(app).provider is None


def test_call_remote_as_an_app_without_rekuest_says_how_to_fix_it(app_dir, monkeypatch):
    class FakeRuntime:
        def get(self, cls):
            return None

    @asynccontextmanager
    async def fake_connect(app, **options):
        yield FakeRuntime()

    monkeypatch.setattr("arkitekt.runtime.connect", fake_connect)

    result = _invoke(app_dir, "call", "remote", "app", "--hash", "abc")

    assert result.exit_code != 0
    assert "arkitekt-cli" in result.output


def test_call_remote_needs_a_hash(app_dir):
    result = _invoke(app_dir, "call", "remote")

    assert result.exit_code != 0
    assert "--hash" in result.output


# --------------------------------------------------------------------------- #
# The app context: --context / --context-file
# --------------------------------------------------------------------------- #

CONTEXT_APP = """
from pydantic import BaseModel

from arkitekt import App


class Config(BaseModel):
    exposure: float = 0.1


app = App("com.test.ctx", "0.0.1", app_context=Config)
config = Config(exposure=0.5)


def make() -> Config:
    return Config(exposure=0.7)


not_a_config = "nope"
"""


@pytest.fixture
def ctx_dir(app_dir):
    (app_dir / "ctx_app.py").write_text(CONTEXT_APP)
    (app_dir / "config.yaml").write_text("exposure: 0.9\n")
    (app_dir / "config.json").write_text('{"exposure": 1.1}')
    return app_dir


def test_prod_hands_the_named_context_to_the_runner(ctx_dir, recorded_runs):
    result = _invoke(ctx_dir, "run", "prod", "ctx_app:app", "--context", "ctx_app:config")

    assert result.exit_code == 0, result.output
    ((app, options),) = recorded_runs
    assert app.identifier == "com.test.ctx"
    assert options["context"].exposure == 0.5


def test_prod_calls_a_context_factory(ctx_dir, recorded_runs):
    result = _invoke(ctx_dir, "run", "prod", "ctx_app:app", "--context", "ctx_app:make")

    assert result.exit_code == 0, result.output
    ((_, options),) = recorded_runs
    assert options["context"].exposure == 0.7


@pytest.mark.parametrize("filename, exposure", [("config.yaml", 0.9), ("config.json", 1.1)])
def test_prod_validates_a_context_file_with_the_declared_class(ctx_dir, recorded_runs, filename, exposure):
    result = _invoke(ctx_dir, "run", "prod", "ctx_app:app", "--context-file", str(ctx_dir / filename))

    assert result.exit_code == 0, result.output
    ((_, options),) = recorded_runs
    assert options["context"].exposure == exposure


def test_prod_refuses_to_run_a_declaring_app_without_a_context(ctx_dir, recorded_runs):
    result = _invoke(ctx_dir, "run", "prod", "ctx_app:app")

    assert result.exit_code != 0
    assert "declares an app context (Config)" in result.output
    assert "--context module:attr or --context-file" in result.output
    assert recorded_runs == []


def test_prod_refuses_a_context_of_the_wrong_class(ctx_dir, recorded_runs):
    result = _invoke(ctx_dir, "run", "prod", "ctx_app:app", "--context", "ctx_app:not_a_config")

    assert result.exit_code != 0
    assert "is a str" in result.output and "Config" in result.output
    assert recorded_runs == []


def test_prod_refuses_both_context_flags(ctx_dir, recorded_runs):
    result = _invoke(
        ctx_dir, "run", "prod", "ctx_app:app",
        "--context", "ctx_app:config", "--context-file", str(ctx_dir / "config.yaml"),
    )

    assert result.exit_code != 0
    assert "not both" in result.output
    assert recorded_runs == []


def test_prod_refuses_a_context_for_an_app_declaring_none(app_dir, recorded_runs):
    (app_dir / "cfg.py").write_text("config = object()\n")
    result = _invoke(app_dir, "run", "prod", "--context", "cfg:config")

    assert result.exit_code != 0
    assert "declares no app context" in result.output
    assert recorded_runs == []
