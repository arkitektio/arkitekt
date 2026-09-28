"""Serving an app over FastAPI is a run whose agent is arkitekt-fastapi's.

The runtime builds it after the app's clients and owns it; the FastAPI lifespan
enters the runtime and provides. An app with no requirements authenticates
nothing, and an action served this way is handed its clients like any other.
"""

import pytest

fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from arkitekt import App, serve  # noqa: E402

from .fakes import PictureClient, PictureService  # noqa: E402


def test_serving_installs_a_lifespan_that_runs_the_app(tmp_path) -> None:  # noqa: ANN001
    from arkitekt_fastapi import FastApiAgent

    app = App("served")
    seen: list = []

    @app.action
    def ping(x: int) -> int:
        """Ping."""
        seen.append(x)
        return x

    fastapi_app = fastapi.FastAPI()
    runtime = serve(app, fastapi_app, db_file=str(tmp_path / "served.db"))
    assert runtime.agent is None, "nothing is built until the app starts"

    with TestClient(fastapi_app):
        agent = runtime.agent
        assert isinstance(agent, FastApiAgent)
        assert agent.bound_app is runtime
        assert agent.app_registry is runtime.snapshot.registry
        assert runtime.fakts is None, "an app with no requirements authenticates nothing"
        assert "ping" in agent.app_registry.implementations
        assert fastapi_app.state.agent is agent

    assert "ping" in app.registry.implementations, "the declaration is untouched"


def test_serving_refuses_a_missing_context_at_the_call() -> None:
    from arkitekt_spec.declare.errors import AppContextError

    class Config:
        pass

    app = App("served-ctx", app_context=Config)
    with pytest.raises(AppContextError, match="none was given"):
        serve(app, fastapi.FastAPI())


def test_a_served_app_with_services_builds_their_clients(tmp_path) -> None:  # noqa: ANN001
    app = App("served-with-clients", services=[PictureService()])

    @app.action
    def show(pictures: PictureClient) -> str:
        """Shows."""
        return pictures.name

    fastapi_app = fastapi.FastAPI()
    runtime = serve(app, fastapi_app, db_file=str(tmp_path / "clients.db"))

    with TestClient(fastapi_app):
        assert runtime.fakts is not None, "a service with a requirement resolves through fakts"
        assert isinstance(runtime.get(PictureClient), PictureClient)
        assert runtime.agent.bound_app is runtime


@pytest.mark.asyncio
async def test_a_served_action_runs_inside_raths_task_scope(tmp_path) -> None:  # noqa: ANN001
    """What the clients an action is handed read to attribute their requests."""
    from arkitekt_fastapi.testing import AsyncAgentTestClient
    from rath.task import current_task

    app = App("served-scope")

    @app.action
    def whose() -> str:
        """Which task this runs as, as rath sees it."""
        task = current_task.get()
        return task.id if task is not None else "none"

    fastapi_app = fastapi.FastAPI()
    serve(app, fastapi_app, db_file=str(tmp_path / "scope.db"))

    async with AsyncAgentTestClient(fastapi_app, as_user="tester") as client:
        result = await client.assign("whose", {})
        events = await client.collect_until_done(result.task_id, timeout=5)

    (returned,) = [e.get_returns() for e in events if e.is_yield()]
    assert returned == {"return0": result.task_id}
