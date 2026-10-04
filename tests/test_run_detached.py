"""A detached run: an app beside a program that has a life of its own.

The host starts it, is told where it stands and cancels it, from whatever thread
it happens to be on. The run owns its thread and its loop; the host owns neither.
"""

import asyncio
import threading
import time
from typing import Annotated, Any, List

import pytest
from aiohttp import web
from arkitekt_spec.declare.app import AppRegistry
from arkitekt_spec.declare.errors import AppContextError
from arkitekt_spec.declare.provider import Provider
from fakts import Alias, Require
from fakts.grants.remote.models import FaktsEndpoint

from arkitekt import (
    App,
    ConnectionState,
    DeviceCodeChallenge,
    has_stored_login,
    logout,
    run_detached,
)
from arkitekt.runtime import DetachedRun, run_manifest

from .fakes import FakeRekuest, write_session

S = ConnectionState


class HeldAgent:
    """An agent that registers and then provides until it is cancelled, or fails first."""

    def __init__(self, fail_with: BaseException | None = None) -> None:
        self.fail_with = fail_with
        self.bound_app: Any = None
        self.force: Any = None
        self.connection_listener: Any = None
        self.task_listener: Any = None
        self.provided: List[Any] = []

    async def aprovide(self, context: Any = None) -> None:  # noqa: ANN401
        self.provided.append(context)
        if self.fail_with is not None:
            raise self.fail_with
        await self.connection_listener(S.REGISTERED)
        await asyncio.Event().wait()

    async def aconnect(self, context: Any = None, timeout: Any = None) -> None:  # noqa: ANN401
        return None

    async def aloop(self) -> None:
        return None

    async def __aenter__(self) -> "HeldAgent":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None


def held_provider(agents: List[HeldAgent], fail_with: List[BaseException]) -> "Provider[HeldAgent]":
    registry = AppRegistry()

    @registry.service()
    def rekuest(rekuest: Annotated[Alias, Require("live.test.rekuest")]) -> FakeRekuest:
        """Rekuest, for tests."""
        return FakeRekuest("rekuest", None)

    @registry.provider()
    def rekuest_agent(registry: AppRegistry, client: FakeRekuest) -> HeldAgent:
        """An agent that stays until cancelled."""
        agent = HeldAgent(fail_with.pop(0) if fail_with else None)
        agents.append(agent)
        return agent

    return rekuest_agent


def held_app(agents: List[HeldAgent], fail_with: List[BaseException] | None = None) -> App[None]:
    app = App("detached", providers=[held_provider(agents, fail_with if fail_with is not None else [])])

    @app.action
    def move(x: int) -> int:
        """Moves."""
        return x

    return app


def _until(predicate, timeout: float = 5.0) -> None:  # noqa: ANN001
    deadline = time.time() + timeout
    while not predicate():
        if time.time() > deadline:
            raise AssertionError("condition not met in time")
        time.sleep(0.01)


def test_it_returns_at_once_and_reports_each_state_until_cancelled() -> None:
    agents: List[HeldAgent] = []
    heard: List[ConnectionState] = []

    async def listener(state: ConnectionState) -> None:
        heard.append(state)

    running = run_detached(held_app(agents), connection_listener=listener)
    try:
        assert running.state in (S.CONNECTING, S.REGISTERED)
        _until(lambda: running.state is S.REGISTERED)
    finally:
        running.cancel()

    assert running.state is S.STOPPED and running.error is None
    assert heard == [S.CONNECTING, S.REGISTERED, S.STOPPED]


def test_it_is_cancelled_from_another_thread_than_the_one_that_started_it() -> None:
    agents: List[HeldAgent] = []
    running = run_detached(held_app(agents))
    _until(lambda: running.state is S.REGISTERED)

    canceller = threading.Thread(target=running.cancel)
    canceller.start()
    canceller.join(timeout=5.0)

    assert not canceller.is_alive()
    assert running.state is S.STOPPED


def test_a_cancelled_run_starts_again_with_the_same_settings() -> None:
    agents: List[HeldAgent] = []
    running = run_detached(held_app(agents))
    _until(lambda: running.state is S.REGISTERED)
    running.cancel()

    running.start()
    try:
        _until(lambda: running.state is S.REGISTERED)
        # A fresh agent each time: a run is never reused.
        assert len(agents) == 2 and agents[0] is not agents[1]
    finally:
        running.cancel()
    assert running.state is S.STOPPED


def test_starting_a_run_that_is_still_going_is_refused() -> None:
    agents: List[HeldAgent] = []
    running = run_detached(held_app(agents))
    try:
        with pytest.raises(RuntimeError, match="still going"):
            running.start()
    finally:
        running.cancel()


def test_a_run_that_fails_says_so_and_can_be_started_again() -> None:
    agents: List[HeldAgent] = []
    heard: List[ConnectionState] = []

    async def listener(state: ConnectionState) -> None:
        heard.append(state)

    running = run_detached(
        held_app(agents, fail_with=[ConnectionError("no route to the lab")]),
        connection_listener=listener,
    )
    _until(lambda: running.state is S.FAILED)

    assert isinstance(running.error, ConnectionError)
    assert heard == [S.CONNECTING, S.FAILED]

    running.start()
    try:
        _until(lambda: running.state is S.REGISTERED)
        assert running.error is None
    finally:
        running.cancel()


def test_cancelling_a_run_that_is_not_going_does_nothing() -> None:
    agents: List[HeldAgent] = []
    running = run_detached(held_app(agents))
    running.cancel()
    running.cancel()
    assert running.state is S.STOPPED


def test_a_listener_that_raises_does_not_end_the_run() -> None:
    agents: List[HeldAgent] = []

    async def listener(state: ConnectionState) -> None:
        raise RuntimeError("the panel is gone")

    running = run_detached(held_app(agents), connection_listener=listener)
    try:
        _until(lambda: running.state is S.REGISTERED)
    finally:
        running.cancel()
    assert running.state is S.STOPPED


def test_the_context_is_checked_at_the_call_not_on_the_runs_thread() -> None:
    class Setup:
        pass

    app = App("detached", app_context=Setup, providers=[held_provider([], [])])

    @app.action
    def move(x: int) -> int:
        """Moves."""
        return x

    with pytest.raises(AppContextError):
        run_detached(app)  # pyright: ignore[reportArgumentType]


def test_a_pending_login_is_handed_to_the_hook_and_then_reported() -> None:
    """The hook first: a listener told of the pending login finds what the hook kept."""
    order: List[str] = []
    kept: List[DeviceCodeChallenge] = []

    async def hook(challenge: DeviceCodeChallenge) -> None:
        kept.append(challenge)
        order.append("hook")

    async def listener(state: ConnectionState) -> None:
        assert kept, "the challenge is known by the time the state is reported"
        order.append(state.value)

    running = run_detached(
        held_app([]), headless=True, device_code_hook=hook, connection_listener=listener
    )
    running.cancel()
    order.clear()

    challenge = DeviceCodeChallenge(
        endpoint=FaktsEndpoint(base_url="https://lab.example/f/", name="Lab"),
        user_code="ABCD-EFGH",
        verification_uri_complete="https://lab.example/f/device/?code=ABCD-EFGH",
        expires_in=300,
    )
    asyncio.run(running._on_device_code(challenge))  # pyright: ignore[reportPrivateUsage]

    assert order == ["hook", "awaiting_login"]
    assert running.state is S.AWAITING_LOGIN
    assert kept[0].verification_uri_complete.endswith("code=ABCD-EFGH")


def test_the_listeners_reach_the_agent() -> None:
    agents: List[HeldAgent] = []

    async def on_task(event: Any) -> None:  # noqa: ANN401
        return None

    running = run_detached(held_app(agents), task_listener=on_task)
    try:
        _until(lambda: running.state is S.REGISTERED)
        assert agents[0].task_listener is on_task
    finally:
        running.cancel()


# --------------------------------------------------------------------------- #
# The stored login
# --------------------------------------------------------------------------- #

LAB = "https://lab.example"


def test_a_login_stored_for_this_declaration_is_found_without_connecting() -> None:
    app = held_app([])
    assert not has_stored_login(app, url=LAB)

    write_session(app.identifier, app.version, LAB, manifest_hash=run_manifest(app).hash())

    assert has_stored_login(app, url=LAB)
    # The same server, written differently, is the same login.
    assert has_stored_login(app, url=LAB + "/")
    assert not has_stored_login(app, url="https://other.example")


def test_a_login_approved_for_another_declaration_is_not_this_apps() -> None:
    app = held_app([])
    write_session(app.identifier, app.version, LAB, manifest_hash="f" * 64)

    assert not has_stored_login(app, url=LAB)


def test_logout_forgets_the_login() -> None:
    app = held_app([])
    write_session(app.identifier, app.version, LAB, manifest_hash=run_manifest(app).hash())

    assert logout(app, url=LAB) is True
    assert not has_stored_login(app, url=LAB)
    assert logout(app, url=LAB) is False


@pytest.mark.revokes
@pytest.mark.asyncio
async def test_logout_revokes_the_login_where_the_server_can() -> None:
    revoked: List[dict[str, str]] = []

    async def revoke(request: web.Request) -> web.Response:
        revoked.append(dict(await request.post()))  # pyright: ignore[reportArgumentType]
        return web.json_response({})

    server = web.Application()
    server.router.add_post("/o/revoke/", revoke)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    base = f"http://127.0.0.1:{runner.addresses[0][1]}"
    try:
        app = held_app([])
        write_session(
            app.identifier, app.version, base, revocation_endpoint=f"{base}/o/revoke/"
        )
        # Called from inside a running loop, as an async host would.
        assert await asyncio.to_thread(logout, app, url=base) is True
    finally:
        await runner.cleanup()

    assert revoked == [
        {"token": "SECRET-REFRESH", "token_type_hint": "refresh_token", "client_id": "client"}
    ]
    assert not has_stored_login(app, url=base)


@pytest.mark.revokes
@pytest.mark.asyncio
async def test_a_login_stored_before_servers_said_where_to_revoke_is_still_revoked() -> None:
    """The stored session names no revocation endpoint: the server is asked for it."""
    revoked: List[dict[str, str]] = []
    base_holder: List[str] = []

    async def well_known(request: web.Request) -> web.Response:
        base = base_holder[0]
        return web.json_response(
            {
                "name": "Lab",
                "version": "2",
                "protocol_version": "2",
                "base_url": f"{base}/f/",
                "issuer": base,
                "token_endpoint": f"{base}/o/token/",
                "device_authorization_endpoint": f"{base}/o/app-authorization/",
                "revocation_endpoint": f"{base}/o/revoke/",
            }
        )

    async def revoke(request: web.Request) -> web.Response:
        revoked.append(dict(await request.post()))  # pyright: ignore[reportArgumentType]
        return web.json_response({})

    server = web.Application()
    server.router.add_get("/.well-known/fakts", well_known)
    server.router.add_post("/o/revoke/", revoke)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    base = f"http://127.0.0.1:{runner.addresses[0][1]}"
    base_holder.append(base)
    try:
        app = held_app([])
        write_session(app.identifier, app.version, base)  # no revocation_endpoint
        assert await asyncio.to_thread(logout, app, url=base) is True
    finally:
        await runner.cleanup()

    assert [form["token"] for form in revoked] == ["SECRET-REFRESH"]


@pytest.mark.revokes
def test_logout_still_forgets_when_the_server_cannot_be_reached() -> None:
    app = held_app([])
    path = write_session(
        app.identifier, app.version, LAB, revocation_endpoint="http://127.0.0.1:1/o/revoke/"
    )

    assert logout(app, url=LAB) is True
    import os

    assert not os.path.exists(path)


def test_a_detached_run_is_what_run_detached_returns() -> None:
    running = run_detached(held_app([]))
    running.cancel()
    assert isinstance(running, DetachedRun)
