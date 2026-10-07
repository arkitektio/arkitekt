"""An app, against a real deployment: logging in, calling a service, offering an action.

Everything else in this repository tests arkitekt against stand-ins. These tests
are the ones that would notice the stand-ins and the servers drifting apart --
fakts negotiating with a real coordination server, a service accepting the token
it issued, an agent registering and being called over a real socket.

They need Docker and the ``konstruktor`` package, and are skipped without either.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import pytest

pytest.importorskip("konstruktor", reason="builds the deployment these tests run against")
pytest.importorskip("rekuest")
pytest.importorskip("mikro")

from konstruktor import Hub  # noqa: E402
from mikro import Mikro, mikro_service  # noqa: E402
from rekuest.arkitekt import rekuest_service  # noqa: E402
from rekuest.client.client import Rekuest  # noqa: E402

from arkitekt.runtime import connect_local  # noqa: E402

from arkitekt import (  # noqa: E402
    App,
    ConnectionState,
    TaskEvent,
    TaskEventKind,
    connect,
    run_detached,
)

pytestmark = [pytest.mark.integration, pytest.mark.konstruktor]

EXAMPLES = Path(__file__).parent.parent.parent / "examples"

#: How long an agent gets to register and answer its first call.
REGISTRATION_TIMEOUT = 90.0


def eventually(attempt: Callable[[], Any], *, timeout: float, still_running: Callable[[], bool]) -> Any:  # noqa: ANN401
    """The result of ``attempt``, retried until it stops raising.

    An agent is registered some time after its run starts, and the only way to
    learn it has happened is that a call goes through. ``still_running`` ends
    the wait at once when the thing being waited for has died, rather than
    after ``timeout``.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            return attempt()
        except Exception:
            if time.monotonic() > deadline or not still_running():
                raise
            time.sleep(1)


def test_an_app_logs_in_and_calls_a_service(hub: Hub) -> None:
    """The whole way in: discovery, a redeemed token, and mikro taking that token."""
    app = App("live.arkitekt.tests.archivist", "0.1.0", services=[mikro_service])

    with connect(app, url=hub.fakts_url, redeem_token=hub.redeem_token("archivist")) as rt:
        folder = rt.require(Mikro).create_folder(name="from the integration suite")

    assert folder.id
    assert folder.name == "from the integration suite"


def test_a_local_run_calls_its_action_with_the_hubs_service(hub: Hub) -> None:
    """What ``hub_call`` of ``arkitekt.testing`` is: the app started for itself, its
    services the deployment's. The action is handed a client that reached mikro
    through a real login, and nothing is registered."""
    app = App("live.arkitekt.tests.librarian", "0.1.0", services=[mikro_service])

    @app.action
    def make_folder(name: str, mikro: Mikro) -> str:
        """Make a folder, and say what it is called"""
        return mikro.create_folder(name=name).name

    with connect_local(
        app, offline=False, url=hub.fakts_url, redeem_token=hub.redeem_token("librarian")
    ) as rt:
        assert rt.call_local("make_folder", name="from a local run") == "from a local run"


def test_an_app_offers_an_action_and_is_called(hub: Hub) -> None:
    """An action registered over the agent socket, called back through the server."""
    app = App("live.arkitekt.tests.shouter", "0.1.0")

    @app.action
    def shout(text: str = "hello") -> str:
        """Shout"""
        return text.upper() + "!"

    with connect(
        app, provide=True, url=hub.fakts_url, redeem_token=hub.redeem_token("shouter")
    ) as rt:
        running = rt.run_detached()
        try:
            answer = eventually(
                lambda: rt.require(Rekuest).call(shout, text="konstruktor"),
                timeout=REGISTRATION_TIMEOUT,
                still_running=lambda: not running.done(),
            )
        finally:
            running.cancel()

    assert answer == "KONSTRUKTOR!"


def test_a_detached_run_is_called_and_tells_its_host(hub: Hub) -> None:
    """``run_detached``: the app beside a program of its own, called through the server.

    The host is told where the connection stands and what the caller did, and
    cancels the run from its own thread -- none of which a stand-in agent proves.
    """
    host = App("live.arkitekt.tests.detached", "0.1.0")

    @host.action
    def whisper(text: str = "hello") -> str:
        """Whispers it back."""
        return text.lower()

    states: list[ConnectionState] = []
    events: list[TaskEvent] = []

    async def on_state(state: ConnectionState) -> None:
        states.append(state)

    async def on_task(event: TaskEvent) -> None:
        events.append(event)

    running = run_detached(
        host,
        url=hub.fakts_url,
        redeem_token=hub.redeem_token("detached"),
        connection_listener=on_state,
        task_listener=on_task,
    )
    caller = App("live.arkitekt.tests.detached-caller", "0.1.0", services=[rekuest_service])
    try:
        with connect(
            caller, url=hub.fakts_url, redeem_token=hub.redeem_token("detached-caller")
        ) as rt:
            rekuest = rt.require(Rekuest)

            def call() -> str:
                (offered,) = [i for i in rekuest.list_implementations() if i.interface == "whisper"]
                return rekuest.call(offered, text="KONSTRUKTOR")

            answer = eventually(
                call,
                timeout=REGISTRATION_TIMEOUT,
                still_running=lambda: running.state is not ConnectionState.FAILED,
            )
    finally:
        running.cancel()

    assert answer == "konstruktor", running.error
    assert running.state is ConnectionState.STOPPED and running.error is None
    assert states[0] is ConnectionState.CONNECTING
    assert ConnectionState.REGISTERED in states and states[-1] is ConnectionState.STOPPED
    assigned = [e for e in events if e.kind is TaskEventKind.ASSIGNED]
    assert assigned and assigned[-1].action == "whisper"
    assert assigned[-1].arguments == {"text": "KONSTRUKTOR"}
    assert events[-1].kind is TaskEventKind.DONE


def test_a_script_run_with_nothing_but_its_environment_is_callable(hub: Hub) -> None:
    """``examples/hello.py``, started the way its docstring says, and called by another app.

    The script is given a server and a redeem token in its environment and
    nothing else -- no browser, no prompt -- which is how an app runs in a
    container. A second app then finds the action it offers and calls it.
    """
    script = subprocess.Popen(
        [sys.executable, str(EXAMPLES / "hello.py")],
        env={**os.environ, **hub.env("hello")},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    caller = App("live.arkitekt.tests.caller", "0.1.0", services=[rekuest_service])

    try:
        with connect(caller, url=hub.fakts_url, redeem_token=hub.redeem_token("caller")) as rt:
            rekuest = rt.require(Rekuest)

            def greet() -> str:
                (offered,) = [i for i in rekuest.list_implementations() if i.interface == "greet"]
                return rekuest.call(offered, name="konstruktor", times=2)

            answer = eventually(
                greet,
                timeout=REGISTRATION_TIMEOUT,
                still_running=lambda: script.poll() is None,
            )
    except Exception:
        script.kill()
        output, _ = script.communicate(timeout=30)
        pytest.fail(f"examples/hello.py was not callable. It said:\n{output}")
    finally:
        if script.poll() is None:
            script.terminate()
            try:
                script.wait(timeout=30)
            except subprocess.TimeoutExpired:
                script.kill()

    assert answer == "Hello konstruktor! Hello konstruktor!"
