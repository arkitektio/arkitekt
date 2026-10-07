"""Checking an app: everything a run would refuse, found without running it."""

from typing import Any, List

import typer
from rich.markup import escape

from arkitekt.app.terminal import done
from arkitekt.cli.commands.app.inspect.utils import run_snapshot_or_exit
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.vars import get_console


def _counted(count: int, what: str) -> str:
    return f"{count} {what}{'' if count == 1 else 's'}"


def summarize(registry: Any) -> str:  # noqa: ANN401
    """What an app declares, in one line: ``3 actions · 1 state · uses mikro``."""
    parts: List[str] = [_counted(len(registry.implementations), "action")]
    states = len(registry.state_registry_schemas)
    if states:
        parts.append(_counted(states, "state"))
    services = sorted(registry.services)
    if services:
        parts.append(f"uses {', '.join(services)}")
    return " · ".join(parts)


def check(ctx: typer.Context, target: TargetArgument = DEFAULT_TARGET) -> None:
    """Check that the app is one a run would accept, without running it.

    Imports the app and validates what it declares the way a run does before it
    connects: every action's arguments and results, every structure and the
    service that resolves it. Nothing is connected or logged in to. Exits with 1
    and says where the problem is otherwise, so it also serves in CI.
    """
    console = get_console(ctx)
    app = load_app_or_exit(ctx, target)
    snapshot = run_snapshot_or_exit(app)
    done(
        console,
        f"{escape(app.identifier)} {escape(app.version)} is valid",
        summarize(snapshot.registry),
    )
