"""`arkitekt run prod` and `arkitekt call remote`: the flags go to the runner, not the App.

The App is the user's declaration. The command line only decides how this run
connects, so the connection flags reach :func:`arkitekt.arun` /
:func:`arkitekt.connect` and the App is left as declared. Nothing connects:
the runner is replaced.
"""

from contextlib import asynccontextmanager

import pytest
from typer.testing import CliRunner

from arkitekt.cli.commands.app.call.remote import parse_call_args
from arkitekt.cli.main import cli_app


@pytest.fixture
def recorded_runs(monkeypatch):
    runs = []

    async def fake_arun(app, **options):
        runs.append((app, options))

    monkeypatch.setattr("arkitekt.runtime.arun", fake_arun)
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
        "--no-cache",
    )

    assert result.exit_code == 0, result.output
    ((app, options),) = recorded_runs
    assert options == {
        "url": "http://fakts.example",
        "token": "client:refresh",
        "headless": True,
        "no_cache": True,
    }
    # The App is not where the connection lives, and the log level is not a
    # connection flag: it configures the process, before the run.
    for flag in ("url", "token", "headless", "log_level", "no_cache"):
        assert not hasattr(app, flag)


def test_prod_shows_the_apps_identity(app_dir, recorded_runs):
    result = _invoke(app_dir, "run", "prod")

    assert "com.test.app:0.0.1" in result.output
    assert "tester" in result.output


def test_prod_without_an_app_module_is_a_clean_error(tmp_path, recorded_runs):
    result = _invoke(tmp_path, "run", "prod")

    assert result.exit_code != 0
    assert "Could not find the app module 'app'" in result.output
    assert recorded_runs == []


def test_a_crashing_run_is_reported(app_dir, monkeypatch):
    async def crash(app, **options):
        raise RuntimeError("boom")

    monkeypatch.setattr("arkitekt.runtime.arun", crash)

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
        app_dir, "call", "remote", "--hash", "abc", "-a", "n=41", "--url", "http://u"
    )

    assert result.exit_code == 0, result.output
    assert seen["app"].identifier == "com.test.app"
    assert seen["options"] == {"url": "http://u"}
    assert seen["hash"] == "abc"
    assert seen["call"] == ({"n": 41}, "the-action")
    assert '"returned": 42' in result.output


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
