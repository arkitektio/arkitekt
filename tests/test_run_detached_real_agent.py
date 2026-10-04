"""A detached run executes real actions: on its own loop, in worker threads, cancellable.

The fakes of ``test_run_detached`` prove the handle. This proves what the handle
is for: a real agent, built by the run on the run's thread, takes a call for a
sync action that reports progress and sleeps cooperatively; the host is told of
each step; and a cancel from the backend stops it where it asks.
"""

import asyncio
import threading
import time
from types import TracebackType
from typing import Annotated, Any, AsyncIterator, List, Optional

import koil
from arkitekt_runtime import messages
from arkitekt_runtime.agents.base import BaseAgent
from arkitekt_runtime.agents.transport.base import AgentTransport
from arkitekt_spec.declare.app import AppRegistry
from fakts import Alias, Require

from arkitekt import App, ConnectionState, Task, TaskEvent, TaskEventKind, run_detached

from .fakes import FakeRekuest

_CLOSED = object()


class Loopback(AgentTransport):
    """A backend in a queue: acknowledges the agent, then delivers what the test feeds."""

    sent: List[Any] = []
    _queue: Optional["asyncio.Queue[object]"] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _host: Any = None
    _connected: bool = False

    def model_post_init(self, __context: object) -> None:
        self.sent = []

    def feed(self, message: object) -> None:
        """From the test's thread: hand the agent a message, as the backend would."""
        assert self._loop is not None and self._queue is not None
        self._loop.call_soon_threadsafe(self._queue.put_nowait, message)

    def set_transport_host(self, host: object) -> None:
        self._host = host

    @property
    def connected(self) -> bool:
        return self._connected

    async def aconnect(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        self._connected = True
        handshake = await self._host.aget_handshake_params()
        self._queue.put_nowait(messages.Init(agent="agent-1", hash=handshake.declaration.hash))

    async def adisconnect(self) -> None:
        self._connected = False
        if self._queue is not None:
            self._queue.put_nowait(_CLOSED)

    async def areceive(self) -> AsyncIterator[messages.ToAgentMessage]:
        assert self._queue is not None
        while True:
            item = await self._queue.get()
            if item is _CLOSED:
                return
            yield item  # type: ignore[misc]

    async def asend(self, message: messages.FromAgentMessage) -> None:
        self.sent.append(message)

    async def __aenter__(self) -> "Loopback":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.adisconnect()


def _until(predicate, timeout: float = 10.0) -> None:  # noqa: ANN001
    deadline = time.time() + timeout
    while not predicate():
        if time.time() > deadline:
            raise AssertionError("condition not met in time")
        time.sleep(0.01)


def _assign(task: str, interface: str, **args: object) -> messages.Assign:
    return messages.Assign(
        task=task,
        interface=interface,
        args=args,
        implementation="impl-1",
        action="action-1",
        reference="ref-1",
        user="user-1",
        org="org-1",
    )


class Pump:
    """The host's own object, handed to the action as the app context."""

    def __init__(self) -> None:
        self.running = False
        self.thread: Optional[str] = None
        self.steps = 0


def test_a_sync_action_runs_reports_and_is_cancelled_where_it_asks() -> None:
    transports: List[Loopback] = []
    registry = AppRegistry()

    @registry.service()
    def rekuest(rekuest: Annotated[Alias, Require("live.test.rekuest")]) -> FakeRekuest:
        """Rekuest, for tests."""
        return FakeRekuest("rekuest", None)

    @registry.provider()
    def agent(registry: AppRegistry, client: FakeRekuest) -> BaseAgent:
        """A real agent over a queue."""
        transport = Loopback()
        transports.append(transport)
        return BaseAgent(transport=transport, app_registry=registry, name="detached")

    app = App("detached-real", app_context=Pump, providers=[agent])

    @app.action
    def dispense(pump: Pump, volume: float, task: Task) -> None:
        """Runs the pump until told to stop."""
        pump.running, pump.thread = True, threading.current_thread().name
        try:
            while True:
                task.check_cancelled()
                task.progress(10, f"{volume} ml")
                koil.sleep(0.01)
                pump.steps += 1
        finally:
            pump.running = False

    states: List[ConnectionState] = []
    events: List[TaskEvent] = []

    async def on_state(state: ConnectionState) -> None:
        states.append(state)

    async def on_task(event: TaskEvent) -> None:
        events.append(event)

    pump = Pump()
    running = run_detached(app, context=pump, connection_listener=on_state, task_listener=on_task)
    try:
        _until(lambda: running.state is ConnectionState.REGISTERED)
        (transport,) = transports

        transport.feed(_assign("task-1", "dispense", volume=2.5))
        _until(lambda: pump.steps > 3)
        assert pump.running
        assert pump.thread != threading.current_thread().name, "the action has a thread of its own"

        transport.feed(messages.Cancel(task="task-1"))
        _until(lambda: any(e.kind is TaskEventKind.CANCELLED for e in events))
        _until(lambda: not pump.running)
    finally:
        running.cancel()

    assert running.state is ConnectionState.STOPPED and running.error is None
    assert states == [
        ConnectionState.CONNECTING,
        ConnectionState.REGISTERED,
        ConnectionState.STOPPED,
    ]
    assert events[0].kind is TaskEventKind.ASSIGNED and events[0].arguments == {"volume": 2.5}
    assert {e.action for e in events} == {"dispense"}
    assert any(e.kind is TaskEventKind.PROGRESS and e.message == "2.5 ml" for e in events)
    assert events[-1].kind is TaskEventKind.CANCELLED
    assert not [e for e in events if e.kind is TaskEventKind.FAILED]
