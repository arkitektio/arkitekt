"""The ``arkitekt self sessions`` command.

Every login saved on this machine, of every app: `arkitekt login` / `logout` see
only the app in the current folder, and an app whose folder is gone still has
its session here.
"""

from typing import Annotated, Optional

import typer
from rich.markup import escape
from rich.table import Table

from arkitekt.app.sessions import forget, list_sessions
from arkitekt.cli.errors import cli_error, confirm_or_abort
from arkitekt.cli.running import ago
from arkitekt.cli.tty import require_tty
from arkitekt.cli.ui import GUTTER, done, notice
from arkitekt.cli.vars import get_console


def sessions(
    ctx: typer.Context,
    forget_name: Annotated[
        Optional[str],
        typer.Option(
            "--forget",
            help="Forget the sessions of this app, as named in the list (on every server).",
        ),
    ] = None,
    forget_all: Annotated[
        bool,
        typer.Option("--all", help="Forget every session on this machine."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Do not ask before forgetting every session."),
    ] = False,
) -> None:
    """List the logins saved on this machine, or forget them

    Forgetting is local: nothing is revoked on the server, and an app that is
    still running saves its session back.
    """
    console = get_console(ctx)
    saved = list_sessions()

    if forget_name is not None or forget_all:
        if forget_name is not None and forget_all:
            cli_error("Pass --forget NAME or --all, not both.")
        chosen = saved if forget_all else [s for s in saved if s.name == forget_name]
        if not chosen:
            notice(console, "Nothing to forget")
            return
        if forget_all and not yes:
            require_tty("Forgetting every session", hint="Pass --yes to do it non-interactively.")
            confirm_or_abort(f"Forget all {len(chosen)} sessions on this machine?")
        for session in chosen:
            forget(session.path)
        done(
            console,
            f"Forgot {len(chosen)} session{'s' if len(chosen) != 1 else ''}",
            "on this machine; nothing is revoked on the server",
        )
        return

    if not saved:
        notice(console, "No sessions on this machine")
        return

    grid = Table.grid(padding=(0, GUTTER, 0, 0))
    # Folded, never cut short: the name is what --forget takes.
    grid.add_column(overflow="fold")
    grid.add_column(overflow="fold")
    grid.add_column(no_wrap=True)
    grid.add_column(no_wrap=True)
    grid.add_row("[dim]app[/]", "[dim]server[/]", "[dim]logged in[/]", "[dim]state[/]")
    for session in saved:
        grid.add_row(
            escape(session.name),
            escape(session.url or "unknown"),
            ago(session.logged_in_at) if session.logged_in_at else "unknown",
            session.state(),
        )
    console.print(grid)
