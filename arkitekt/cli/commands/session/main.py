"""`arkitekt login`, `logout` and `status`: the session of the app in this folder.

A session is what a login leaves behind, cached per app, version and server
(:mod:`arkitekt.app.sessions`). A run logs in by itself when it has none; these
commands let that be done, undone and looked at without running the app.
"""

import asyncio
from typing import Any, Optional

import typer
from rich.console import Console
from rich.markup import escape

from arkitekt import runtime
from arkitekt.app.fakts import resolve_url
from arkitekt.app import App
from arkitekt.app.sessions import Session, read_session, session_path
from arkitekt.cli.commands.app.run.utils import explicit_options
from arkitekt.cli.failures import report_failure
from arkitekt.cli.options import (
    HeadlessOption,
    LogLevel,
    LogLevelOption,
    ReauthOption,
    RedeemTokenOption,
    TokenOption,
    UrlOption,
)
from arkitekt.cli.running import ago
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.ui import construct_app_banner, done, notice
from arkitekt.cli.utils import configure_logging
from arkitekt.cli.vars import get_console
from arkitekt.constants import DEFAULT_ARKITEKT_URL

#: The connection flags a login takes: how to reach the server and as whom.
LOGIN_OPTIONS = ("url", "token", "redeem_token", "headless")


def _usable_session(console: Console, app: App[Any], server: str) -> Optional[Session]:
    """The saved session a run of ``app`` against ``server`` would use, if any.

    One is saved per app, version and server, for the manifest it was approved
    with. A run whose manifest differs logs in again, so that session is not
    this app's any more.
    """
    session = read_session(session_path(app.identifier, app.version, server))
    if session is None:
        return None
    try:
        expected = runtime.run_manifest(app).hash()
    except Exception as e:
        if report_failure(console, e):
            raise typer.Exit(code=1) from None
        raise
    return session if session.is_for(expected) else None


def login(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    url: UrlOption = DEFAULT_ARKITEKT_URL,
    token: TokenOption = None,
    redeem_token: RedeemTokenOption = None,
    headless: HeadlessOption = False,
    reauth: ReauthOption = False,
    log_level: LogLevelOption = LogLevel.ERROR,
) -> None:
    """Log this folder's app in, and save the session

    A run does this by itself the first time. Logging in ahead of it saves the
    session without starting the app, and with --reauth replaces the one saved:
    for a wrong user or organization.
    """
    console = get_console(ctx)
    configure_logging(log_level.value)
    app = load_app_or_exit(ctx, target)
    options = explicit_options(ctx, LOGIN_OPTIONS)
    server = resolve_url(options.get("url"))
    console.print(construct_app_banner(app, server, connection="logging in to"))

    session = _usable_session(console, app, server)
    if session is not None and session.state() == "active" and not reauth:
        since = f"{ago(session.logged_in_at)} · " if session.logged_in_at else ""
        done(console, "Already logged in", f"{since}--reauth logs in again")
        return

    try:
        # A login asked for by name always logs in: a saved session is replaced.
        # Through the module, so the login stays replaceable (tests patch it).
        loaded = asyncio.run(runtime.alogin(app, reauth=True, **options))
    except KeyboardInterrupt:
        raise typer.Exit(code=1) from None
    except Exception as e:
        if report_failure(console, e):
            raise typer.Exit(code=1) from None
        raise

    if options.get("token") or options.get("redeem_token"):
        # An interactive login has said so itself, when it was approved.
        done(console, f"Logged in to {escape(loaded.self.deployment_name)}", "with a token")


def logout(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    url: UrlOption = DEFAULT_ARKITEKT_URL,
) -> None:
    """Revoke and forget the saved session of this folder's app

    The next run logs in again. The session is revoked on a server that offers
    that, and forgotten on this machine either way. Stop an instance of the app
    that is still running first: it saves its session back.
    """
    console = get_console(ctx)
    app = load_app_or_exit(ctx, target)
    server = resolve_url(explicit_options(ctx, ("url",)).get("url"))

    if not runtime.logout(app, url=server):
        notice(
            console,
            "Not logged in",
            f"{escape(app.identifier)} has no session for {escape(server)}",
        )
        return
    done(
        console,
        f"Logged out of {escape(server)}",
        f"{escape(app.identifier)} {escape(app.version)}",
    )
    notice(console, "Stop running instances", "one still running saves its session back")


def status(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    url: UrlOption = DEFAULT_ARKITEKT_URL,
) -> None:
    """Show this folder's app and whether it is logged in"""
    console = get_console(ctx)
    app = load_app_or_exit(ctx, target)
    server = resolve_url(explicit_options(ctx, ("url",)).get("url"))
    console.print(construct_app_banner(app, server, connection="server"))

    saved = read_session(session_path(app.identifier, app.version, server))
    session = _usable_session(console, app, server)
    if session is None:
        if saved is not None:
            # Saved for the app as it was declared then: a scope, a service or
            # the device has changed since, and the server approves each anew.
            notice(
                console,
                "The saved session is for another declaration of this app",
                "the next run logs in again",
            )
            return
        notice(console, "Not logged in", "`arkitekt login`, or just run the app")
        return

    since = f"{ago(session.logged_in_at)} · " if session.logged_in_at else ""
    state = session.state()
    if state == "active":
        done(console, "Logged in", f"{since}{escape(session.deployment)}")
    else:
        # Too old to renew, as far as this machine can tell: the next run asks again.
        notice(
            console,
            f"The saved session is {state}",
            f"logged in {since}`arkitekt login --reauth` replaces it",
        )
