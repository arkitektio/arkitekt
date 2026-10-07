"""A local run: the app started for itself, its actions called through its own agent."""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

import pytest

from arkitekt import App
from arkitekt.runtime import connect, connect_local
from arkitekt.testing import LocalCallError, local_app

from .fakes import Picture, PictureClient, PictureService


def build_app(log: List[str], built: List[Any]) -> App[None]:
    app = App("local-run", "0.1.0", services=[PictureService(built=built)])

    @app.action
    def add(a: int, b: int = 2) -> int:
        """Add"""
        return a + b

    @app.action
    async def client_name(pictures: PictureClient) -> str:
        """The name of the client the action was handed"""
        return pictures.name

    @app.action
    def owner(picture: Picture) -> str:
        """Who a picture, expanded by the service's client, belongs to"""
        return picture.owner

    @app.action
    def broken() -> str:
        """Raises"""
        raise RuntimeError("no luck")

    @app.startup
    async def started():  # noqa: ANN202 -- a hook's return annotation names what it provides
        log.append("startup")

    @app.shutdown
    async def stopped():  # noqa: ANN202
        log.append("shutdown")

    return app


@pytest.fixture()
def log() -> List[str]:
    return []


@pytest.fixture()
def built() -> List[Any]:
    return []


@pytest.fixture()
def app(log: List[str], built: List[Any]) -> App[None]:
    return build_app(log, built)


def test_an_action_is_called_by_function_and_by_name(app: App[None]) -> None:
    with local_app(app) as rt:
        assert rt.call_local("add", 1) == 3
        assert rt.call_local(app.registry.get_declared_implementation("add").function, a=1, b=1) == 2


@pytest.mark.asyncio
async def test_it_is_called_from_async_code_too(app: App[None]) -> None:
    async with local_app(app) as rt:
        assert await rt.acall_local("add", 2, 2) == 4
        assert [value async for value in rt.aiterate_local("add", 1)] == [3]


def test_the_app_is_started_and_stopped_around_the_run(app: App[None], log: List[str]) -> None:
    with local_app(app) as rt:
        assert log == ["startup"]
        rt.call_local("add", 1)
    assert log == ["startup", "shutdown"]


def test_a_replaced_client_is_what_actions_and_expanders_get(app: App[None], built: List[Any]) -> None:
    fake = PictureClient("fake")
    with local_app(app, clients=[fake]) as rt:
        assert rt.require(PictureClient) is fake
        assert rt.call_local("client_name") == "fake"
        assert rt.call_local("owner", Picture("7", "somebody")) == "fake"
    assert built == [], "the service it replaces is never built"


def test_a_replaced_client_is_entered_and_left_with_the_run(app: App[None]) -> None:
    """What a client of a real service, started for a test, relies on: its lifetime is the run's."""
    client = PictureClient("real")
    with local_app(app, clients=[client]):
        assert client.log == ["enter real"]
    assert client.log == ["enter real", "exit real"]


def test_a_service_that_is_not_replaced_points_nowhere(app: App[None], monkeypatch: pytest.MonkeyPatch) -> None:
    """Offline builds its own fakts: the deployment's is never asked for."""

    def never(manifest: Any, options: Any) -> None:  # noqa: ANN401
        raise AssertionError("an offline run built the deployment's fakts")

    monkeypatch.setattr("arkitekt.runtime.build_fakts", never)
    with local_app(app) as rt:
        assert rt.call_local("client_name") == "pictures-1"


def test_a_raising_action_raises_in_the_test(app: App[None]) -> None:
    with local_app(app) as rt, pytest.raises(LocalCallError, match="no luck"):
        rt.call_local("broken")


def test_an_unknown_action_names_the_ones_there_are(app: App[None]) -> None:
    with local_app(app) as rt, pytest.raises(KeyError, match="add"):
        rt.call_local("subtract")


def test_only_a_local_run_calls_in_process(app: App[None]) -> None:
    with connect(app) as rt, pytest.raises(LookupError, match="connect_local"):
        rt.call_local("add", 1)


def test_a_local_run_that_is_not_offline_builds_the_deployments_fakts(
    app: App[None], built: List[Any]
) -> None:
    """The conftest's stand-in for the deployment's fakts is what it gets."""
    with connect_local(app, offline=False) as rt:
        assert rt.call_local("client_name") == "pictures-1"


@dataclass
class Settings:
    factor: int


def test_the_app_context_reaches_the_actions() -> None:
    app = App("local-context", "0.1.0", app_context=Settings)

    @app.action
    def scale(number: int, settings: Settings) -> int:
        """Scale"""
        return number * settings.factor

    with local_app(app, context=Settings(factor=3)) as rt:
        assert rt.call_local("scale", 2) == 6


PROJECT_APP = '''
from arkitekt import App

app = App("fixture-app", "0.1.0")


@app.action
def add(a: int, b: int = 2) -> int:
    """Add"""
    return a + b
'''

PROJECT_TEST = '''
from app import add


def test_by_name(call):
    assert call("add", 1) == 3


def test_by_function(call):
    assert call(add, a=1, b=1) == 2
'''


def test_the_pytest_fixtures_find_and_call_the_projects_app(tmp_path: Path) -> None:
    """In a process of its own: the plugin is loaded the way a project loads it."""
    (tmp_path / "app.py").write_text(PROJECT_APP)
    (tmp_path / "conftest.py").write_text('pytest_plugins = ["arkitekt.testing"]\n')
    (tmp_path / "test_app.py").write_text(PROJECT_TEST)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}
    env.pop("ARKITEKT_APP", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", str(tmp_path), str(tmp_path)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 passed" in result.stdout


PROJECT_STACK_TEST = '''
from arkitekt.testing import TestStack


def test_annotated(call, request):
    annotation: type[TestStack[None]] = TestStack[None]
    assert annotation is not None
'''


def test_importing_teststack_into_a_test_module_is_not_collected(tmp_path: Path) -> None:
    """Its name starts with ``Test``: pytest must not take it for a test class."""
    (tmp_path / "app.py").write_text(PROJECT_APP)
    (tmp_path / "conftest.py").write_text('pytest_plugins = ["arkitekt.testing"]\n')
    (tmp_path / "test_app.py").write_text(PROJECT_STACK_TEST)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}
    env.pop("ARKITEKT_APP", None)
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
            "-W", "error::pytest.PytestCollectionWarning",
            "--rootdir", str(tmp_path), str(tmp_path),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout


def test_a_connected_local_run_is_the_app_a_providing_run_logs_in_as(app: App[None]) -> None:
    """Same manifest, so the same saved session: a local call neither asks for a
    second login nor replaces the one `run` made."""
    pytest.importorskip("rekuest")

    local = connect_local(app, offline=False)._prepare().manifest
    providing = connect(app, provide=True)._prepare().manifest

    assert local.hash() == providing.hash()
    assert {r.key for r in local.requirements or []} >= {"rekuest"}


def test_a_local_run_of_an_app_without_services_reaches_no_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """The provider's own service is not a reason to log in: the local agent talks to nobody."""
    bare = App("local-bare", "0.1.0")

    @bare.action
    def add(a: int, b: int = 2) -> int:
        """Add"""
        return a + b

    def never(manifest: Any, options: Any) -> None:  # noqa: ANN401
        raise AssertionError("a local run of an app without services built the deployment's fakts")

    monkeypatch.setattr("arkitekt.runtime.build_fakts", never)
    with connect_local(bare, offline=False) as rt:
        assert rt.call_local("add", 1) == 3
