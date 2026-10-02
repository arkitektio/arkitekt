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

from konstruktor import Hub  # noqa: E402  # pyright: ignore[reportMissingImports]
from mikro import Mikro, mikro_service  # noqa: E402
from rekuest.arkitekt import rekuest_service  # noqa: E402
from rekuest.client.client import Rekuest  # noqa: E402

from arkitekt import App, connect  # noqa: E402

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
