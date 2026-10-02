"""Connecting an app from the CLI, and saying what happens to the connection.

After the banner a run says how it got its session (a login, or one it had), and,
when it provides, when the server has registered its agent and when the link to
it drops and returns. The commands connect through here instead of handing the
whole run to :func:`arkitekt.arun`, which says nothing.
"""

import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

from rich.console import Console
from rich.markup import escape

from arkitekt import runtime
from arkitekt.app import App
from arkitekt.app.fakts import resolve_url
from arkitekt.app.sessions import read_session, session_path
from arkitekt.app.terminal import done, notice


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
            done(
                self.console,
                "Registered",
                f"providing {offered} action{'s' if offered != 1 else ''}",
            )


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
    console: Console, app: App[Any], options: Dict[str, Any], provide: bool = False
) -> AsyncIterator[Any]:
    """Connect ``app`` with the explicitly passed ``options``, and report on it.

    Args:
        console: Where to report.
        app: The app to connect.
        options: The connection flags the user passed (see ``runner_options``).
        provide: Whether the run provides the app's offerings; it then also
            reports on its agent's connection.
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
    # Through the module, so the connection stays replaceable (tests patch it).
    async with runtime.connect(app, **options, **extra) as rt:
        report_session(console, rt, before, options)
        yield rt


async def arun_app(
    console: Console,
    app: App[Any],
    options: Dict[str, Any],
    context: Any = None,  # noqa: ANN401
) -> None:
    """Connect ``app`` and provide its offerings until stopped, reporting as it goes."""
    async with connected(console, app, options, provide=True) as rt:
        await rt.arun(context=context)


__all__ = ["ConnectionReporter", "ago", "arun_app", "connected", "logged_in_at", "report_session"]
