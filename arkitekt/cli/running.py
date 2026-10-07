"""Connecting an app from the CLI, and saying what happens to the connection.

After the banner a run says how it got its session (a login, or one it had), and,
when it provides, when the server has registered its agent and when the link to
it drops and returns. The commands connect through here instead of handing the
whole run to :func:`arkitekt.arun`, which says nothing.
"""

import os
import sys
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator, Dict, Iterator, Optional

from rich.console import Console
from rich.markup import escape

from arkitekt import runtime
from arkitekt.app import App
from arkitekt.app.fakts import resolve_url
from arkitekt.app.sessions import read_session, session_path
from arkitekt.app.terminal import done, fail, notice, step


def ago(moment: float, now: Optional[float] = None) -> str:
    """How long ago ``moment`` (a unix timestamp) was, in words."""
    seconds = max(0.0, (time.time() if now is None else now) - moment)
    for unit, length in (("day", 86400), ("hour", 3600), ("minute", 60)):
        count = int(seconds // length)
        if count:
            return f"{count} {unit}{'s' if count != 1 else ''} ago"
    return "just now"


def logged_in_at(app: App[Any], url: str) -> Optional[float]:
    """When the session ``app`` has cached for ``url`` was logged in, if it has one."""
    session = read_session(session_path(app.identifier, app.version, url))
    return session.logged_in_at if session else None


class ConnectionReporter:
    """Says when the app's agent is registered, loses its link, and is back."""

    def __init__(self, console: Console, app: App[Any]) -> None:
        self.console = console
        self.app = app
        self.registered_before = False

    async def __call__(self, state: Any) -> None:  # noqa: ANN401
        # By value: the states are arkitekt-runtime's, which only a run needs.
        if getattr(state, "value", state) == "disconnected":
            notice(self.console, "Connection lost, reconnecting")
        elif self.registered_before:
            done(self.console, "Reconnected")
        else:
            self.registered_before = True
            offered = len(self.app.registry.get_implementations())
            names = sorted(i.interface or "" for i in self.app.registry.get_implementations())
            listed = ", ".join(names[:6]) + (f" and {len(names) - 6} more" if len(names) > 6 else "")
            done(
                self.console,
                "Registered",
                f"providing {offered} action{'s' if offered != 1 else ''}"
                + (f": {escape(listed)}" if names else ""),
            )


class TaskReporter:
    """Says when the app takes a task, and how it ended.

    While developing, this is how one sees that a call arrived at all. A failing
    action's traceback is the runtime's to log; this is the line that names it.
    """

    def __init__(self, console: Console) -> None:
        self.console = console
        self.started: Dict[str, float] = {}

    async def __call__(self, event: Any) -> None:  # noqa: ANN401
        # By value: the kinds are arkitekt-spec's agent module, which only a run needs.
        kind = getattr(event.kind, "value", event.kind)
        action = escape(event.action)
        if kind == "assigned":
            self.started[event.task_id] = time.monotonic()
            arguments = " ".join(
                f"{key}={_short(value)}" for key, value in (event.arguments or {}).items()
            )
            step(self.console, action, escape(arguments) or None)
            return
        if kind not in ("done", "failed", "cancelled"):
            return
        began = self.started.pop(event.task_id, None)
        took = f"{_elapsed(time.monotonic() - began)}" if began is not None else None
        if kind == "done":
            done(self.console, action, took)
        elif kind == "cancelled":
            notice(self.console, f"{action} cancelled", took)
        else:
            fail(self.console, f"{action} failed", escape(event.error or ""))


def _short(value: Any, limit: int = 40) -> str:  # noqa: ANN401
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _elapsed(seconds: float) -> str:
    return f"{seconds * 1000:.0f} ms" if seconds < 1 else f"{seconds:.1f} s"


def report_session(
    console: Console, rt: Any, before: Optional[float], options: Dict[str, Any]
) -> None:  # noqa: ANN401
    """Say how the run got its session, unless the login prompt already did.

    ``before`` is when the session the app had cached was logged in. The run's
    session started then: it was reused. It started later: the app logged in
    just now, which an interactive login has already said.
    """
    loaded = getattr(getattr(rt, "fakts", None), "loaded_fakts", None)
    if loaded is None:
        return
    started = loaded.auth.chain_started_at
    if before is not None and started == before:
        done(
            console,
            "Session reused",
            f"logged in {ago(started)} · `arkitekt logout` ends it",
        )
    elif options.get("token") or options.get("redeem_token"):
        done(console, f"Logged in to {escape(loaded.self.deployment_name)}", "with a token")


@asynccontextmanager
async def connected(
    console: Console,
    app: App[Any],
    options: Dict[str, Any],
    provide: bool = False,
    tasks: bool = False,
) -> AsyncIterator[Any]:
    """Connect ``app`` with the explicitly passed ``options``, and report on it.

    Args:
        console: Where to report.
        app: The app to connect.
        options: The connection flags the user passed (see ``runner_options``).
        provide: Whether the run provides the app's offerings; it then also
            reports on its agent's connection.
        tasks: Whether a providing run also reports each task it takes.
    """
    url = resolve_url(options.get("url"))
    fresh = options.get("skip_cache") or options.get("reauth")
    before = None if fresh else logged_in_at(app, url)
    # Only what a providing run needs is added: a script-like connection is made
    # with exactly what the user passed.
    extra: Dict[str, Any] = (
        {"provide": True, "connection_listener": ConnectionReporter(console, app)}
        if provide
        else {}
    )
    if provide and tasks:
        extra["task_listener"] = TaskReporter(console)
    # Through the module, so the connection stays replaceable (tests patch it).
    async with runtime.connect(app, **options, **extra) as rt:
        report_session(console, rt, before, options)
        yield rt


@asynccontextmanager
async def connected_local(
    console: Console,
    app: App[Any],
    options: Dict[str, Any],
    offline: bool = True,
    context: Any = None,  # noqa: ANN401
) -> AsyncIterator[Any]:
    """Start ``app`` for itself, to call its own actions in: nothing is registered.

    Args:
        console: Where to report.
        app: The app to start.
        options: The connection flags the user passed, for the services it uses.
        offline: Reach no server; the app's services then point nowhere.
        context: The app context, for an app that declares one.
    """
    url = resolve_url(options.get("url"))
    fresh = options.get("skip_cache") or options.get("reauth")
    before = None if fresh or offline else logged_in_at(app, url)
    # Through the module, so the connection stays replaceable (tests patch it).
    async with runtime.connect_local(app, offline=offline, context=context, **options) as rt:
        if not offline:
            report_session(console, rt, before, options)
        yield rt


async def arun_app(
    console: Console,
    app: App[Any],
    options: Dict[str, Any],
    context: Any = None,  # noqa: ANN401
    tasks: bool = False,
) -> None:
    """Connect ``app`` and provide its offerings until stopped, reporting as it goes.

    With ``tasks`` each task the app takes is reported too: what a developer
    watching the terminal wants, and noise in the log of a deployed app.
    """
    async with connected(console, app, options, provide=True, tasks=tasks) as rt:
        await rt.arun(context=context)


#: What the workers of an event loop's own thread pool are called: where a
#: blocking action runs.
_WORKER_PREFIX = "asyncio_"


def _workers() -> set[threading.Thread]:
    return {t for t in threading.enumerate() if t.name.startswith(_WORKER_PREFIX)}


@contextmanager
def interruptible(console: Console) -> Iterator[None]:
    """A run that Ctrl+C ends: the first stops it, a second one does not wait.

    The first Ctrl+C stops the app and is waited for. What can not be stopped is
    a blocking action that never checks whether it was cancelled: its thread
    outlives the app, and the interpreter waits for every such thread before it
    exits. A second Ctrl+C then leaves without it.
    """
    before = _workers()
    try:
        yield
    except KeyboardInterrupt:
        if _workers() - before:
            notice(console, "Stopped", "not waiting for a task that did not stop")
            sys.stdout.flush()
            sys.stderr.flush()
            # The only way past the threads the interpreter would wait for.
            os._exit(130)


__all__ = [
    "ConnectionReporter",
    "TaskReporter",
    "ago",
    "arun_app",
    "interruptible",
    "connected",
    "connected_local",
    "logged_in_at",
    "report_session",
]
