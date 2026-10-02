"""A run is a Runtime: it snapshots the app, builds its clients and binds them.

The app is never changed by running it, so it runs any number of times, and two
runs of one app never share a client. Every client comes from its service's
builder; the fakts they resolve through is the offline one every test gets
(``conftest``), so nothing here talks to a server.
"""

import asyncio
from typing import Any

import pytest
from arkitekt_spec.declare.errors import RegistryFrozenError
from arkitekt_spec.declare.service import Service

from arkitekt import App, connect, run

from .fakes import (
    FakeAgent,
    FakeRekuest,
    OtherClient,
    OtherService,
    Picture,
    PictureClient,
    PictureService,
    RekuestProvider,
)


def picture_app(service: Service[Any] | None = None) -> App[None]:
    """An app using pictures (and a fake rekuest provider, since it offers an action)."""
    app = App("runtime", services=[service or PictureService()], providers=[RekuestProvider()])

    @app.action
    def show(picture: Picture) -> str:
        """Shows it."""
        return picture.id

    return app


def test_connect_builds_nothing_until_entered() -> None:
    built: list[PictureClient] = []
    runtime = connect(picture_app(PictureService(built)))
    assert built == [] and runtime.clients == {}


@pytest.mark.asyncio
async def test_entering_builds_one_client_per_service() -> None:
    built: list[PictureClient] = []
    async with connect(picture_app(PictureService(built))) as rt:
        assert built == [rt.get(PictureClient)]
        assert isinstance(rt.get(FakeRekuest), FakeRekuest)
        assert set(rt.clients) == {"pictures", "rekuest"}


@pytest.mark.asyncio
async def test_a_run_binds_its_snapshot_to_its_own_clients() -> None:
    app = picture_app()

    async with connect(app) as a:
        async with connect(app) as b:
            assert a.snapshot is not None and b.snapshot is not None, "entered runs have one"
            from_a, from_b = await asyncio.gather(
                a.snapshot.registry.structure_registry.get_fullfilled_structure("@pictures/picture").expand("1"),
                b.snapshot.registry.structure_registry.get_fullfilled_structure("@pictures/picture").expand("2"),
            )

    assert (from_a.owner, from_b.owner) == ("pictures-1", "pictures-2")
    assert a.get(PictureClient) is not b.get(PictureClient)
    # The declaration is never bound: a run binds copies of its entries.
    declared = app.registry.structure_registry.get_fullfilled_structure("@pictures/picture")
    assert a.snapshot is not None
    bound_in_a = a.snapshot.registry.structure_registry.get_fullfilled_structure("@pictures/picture")
    assert bound_in_a is not declared
    assert declared.aexpand is not bound_in_a.aexpand


@pytest.mark.asyncio
async def test_the_app_stays_open_while_its_run_is_frozen() -> None:
    app = picture_app()
    async with connect(app) as rt:
        assert rt.snapshot is not None

        def later(x: int) -> int:
            """Declared while running."""
            return x

        with pytest.raises(RegistryFrozenError):
            rt.snapshot.registry.register(later)
        app.action(later)

    assert "later" in app.registry.implementations
    assert rt.snapshot is not None
    assert "later" not in rt.snapshot.registry.implementations


@pytest.mark.asyncio
async def test_entering_enters_every_client_and_leaves_them_in_reverse() -> None:
    log: list[str] = []
    app = App("order", services=[PictureService(log=log), OtherService(log=log)])

    async with connect(app) as rt:
        assert rt.require(PictureClient).name == "pictures-1"

    assert log == ["enter pictures-1", "enter other", "exit other", "exit pictures-1"]


@pytest.mark.asyncio
async def test_a_runtime_is_used_once() -> None:
    runtime = connect(App("once"))
    async with runtime:
        pass
    with pytest.raises(RuntimeError, match="already used"):
        async with runtime:
            pass


@pytest.mark.asyncio
async def test_a_failing_client_leaves_what_was_entered() -> None:
    log: list[str] = []

    class Broken(OtherClient):
        async def __aenter__(self) -> "Broken":
            raise ConnectionError("down")

    app = App("broken", services=[PictureService(log=log), OtherService(log=log, client_cls=Broken)])
    with pytest.raises(ConnectionError):
        async with connect(app):
            pass
    assert log == ["enter pictures-1", "exit pictures-1"]


@pytest.mark.asyncio
async def test_the_run_builds_binds_and_drives_the_agent() -> None:
    app = picture_app()
    # Declared on the registry, past the App's type parameter: the checker still
    # sees App[None], so the context the run is handed is untyped here.
    app.registry.app_context(str)
    async with connect(app, provide=True, force=True) as rt:
        agent = rt.agent
        assert isinstance(agent, FakeAgent)
        assert agent.client is rt.get(FakeRekuest), "built from the run's own client"
        assert agent.bound_app is rt and agent.force is True
        await rt.arun(context="ctx")  # pyright: ignore[reportCallIssue, reportArgumentType]
    assert agent.provided == ["ctx"]


class Config:
    def __init__(self, label: str = "cfg") -> None:
        self.label = label


@pytest.mark.asyncio
async def test_a_run_refuses_the_wrong_context_before_the_agent_starts() -> None:
    from arkitekt_spec.declare.errors import AppContextError

    app = App("ctx", services=[PictureService()], providers=[RekuestProvider()], app_context=Config)
    async with connect(app, provide=True) as rt:
        agent = rt.agent
        assert isinstance(agent, FakeAgent)
        # The wrong contexts are the point: the checker refuses them too.
        with pytest.raises(AppContextError, match="none was given"):
            await rt.arun()  # pyright: ignore[reportCallIssue]
        with pytest.raises(AppContextError, match="was given a str"):
            await rt.arun(context="no")  # pyright: ignore[reportArgumentType]
        assert agent.provided == []
        await rt.arun(context=Config("yes"))
    assert [c.label for c in agent.provided] == ["yes"]

    plain = picture_app()
    async with connect(plain, provide=True) as rt:
        with pytest.raises(AppContextError, match="declares no app context"):
            await rt.arun(context=Config())  # pyright: ignore[reportCallIssue, reportArgumentType]


def test_run_refuses_a_missing_context_before_logging_in(monkeypatch: pytest.MonkeyPatch) -> None:
    from arkitekt_spec.declare.errors import AppContextError

    def never(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise AssertionError("fakts must not be built for a run that cannot start")

    monkeypatch.setattr("arkitekt.runtime.build_fakts", never)
    app = App("ctx", services=[PictureService()], providers=[RekuestProvider()], app_context=Config)
    with pytest.raises(AppContextError, match="none was given"):
        # The missing context is the point.
        run(app)  # pyright: ignore[reportArgumentType]


@pytest.mark.asyncio
async def test_the_agent_enters_after_the_clients_and_leaves_first() -> None:
    log: list[str] = []
    app = App("order", services=[PictureService(log=log)], providers=[RekuestProvider(log)])
    async with connect(app, provide=True):
        pass
    assert log == ["enter pictures-1", "enter rekuest", "enter agent", "exit agent", "exit rekuest", "exit pictures-1"]


@pytest.mark.asyncio
async def test_an_app_offering_nothing_has_nothing_to_run() -> None:
    app = App("script", services=[PictureService()])
    async with connect(app, provide=True) as rt:
        assert rt.agent is None
        with pytest.raises(LookupError, match="offers nothing"):
            await rt.arun()


@pytest.mark.asyncio
async def test_connecting_builds_no_agent_even_for_an_app_that_offers() -> None:
    async with connect(picture_app()) as rt:
        assert rt.agent is None and rt.provider is None
        with pytest.raises(LookupError, match="without providing"):
            await rt.arun()


def test_running_an_app_that_declares_no_provider_serves_it_through_rekuest() -> None:
    from rekuest.arkitekt import rekuest_provider

    app = App("plain")

    @app.action
    def double(x: int) -> int:
        """Doubles."""
        return x * 2

    assert "rekuest" not in app.services and not app.registry.providers
    runtime = connect(app, provide=True)
    assert runtime.provider is rekuest_provider

    snapshot = app.snapshot(provider=runtime.provider)
    assert "rekuest" in snapshot.services and snapshot.provider is rekuest_provider
    assert snapshot.manifest.requirements is not None
    assert {r.key for r in snapshot.manifest.requirements} >= {"rekuest", "s3"}
    assert app.manifest.requirements == [], "the declaration is unchanged"


@pytest.mark.asyncio
async def test_an_app_with_no_requirements_authenticates_nothing() -> None:
    async with connect(App("bare")) as rt:
        assert rt.fakts is None


@pytest.mark.asyncio
async def test_require_names_the_service_to_register() -> None:
    async with connect(App("bare")) as rt:
        assert rt.get(PictureClient) is None
        with pytest.raises(LookupError, match="PictureClient"):
            rt.require(PictureClient)


@pytest.mark.asyncio
async def test_the_runtime_manifest_adds_the_device_id() -> None:
    app = App("node")
    async with connect(app, device_id="machine-1") as rt:
        assert rt.snapshot is not None
        assert rt.snapshot.manifest.device_id == "machine-1"
        assert rt.snapshot.manifest.identifier == "node"
    assert app.manifest.device_id is None


@pytest.mark.asyncio
async def test_a_run_writes_nothing_into_the_working_directory(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The working directory is process-wide state; a run leaves it alone."""
    monkeypatch.chdir(tmp_path)

    async with connect(picture_app()):
        pass

    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_a_run_hands_its_connection_listener_to_its_agent() -> None:
    async def listener(state: Any) -> None:  # noqa: ANN401
        return None

    async with connect(picture_app(), provide=True, connection_listener=listener) as rt:
        assert rt.agent is not None
        assert rt.agent.connection_listener is listener

    # None given: the agent is left as its provider built it.
    async with connect(picture_app(), provide=True) as rt:
        assert not hasattr(rt.agent, "connection_listener")
