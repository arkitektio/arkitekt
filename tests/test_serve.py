"""Serving an app over FastAPI is a run whose agent is rekuest's FastAPI agent.

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
    from rekuest.contrib.fastapi import FastApiAgent

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
