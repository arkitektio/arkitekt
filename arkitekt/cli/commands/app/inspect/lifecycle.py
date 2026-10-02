import json
from typing import Annotated, Any

import typer
from rich.tree import Tree

from arkitekt.cli.commands.app.inspect.utils import NOTHING_TO_PROVIDE
from arkitekt.cli.errors import cli_error
from arkitekt.cli.utils import emit_machine_readable
from arkitekt.cli.vars import get_console
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit


def _records(hooks: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "name": name,
            "module": getattr(fn, "__module__", ""),
            "qualname": getattr(fn, "__qualname__", ""),
        }
        for name, fn in hooks.items()
    ]


def lifecycle(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    pretty: Annotated[
        bool,
        typer.Option("--pretty", "-p", help="Should we just output json?"),
    ] = False,
    machine_readable: Annotated[
        bool,
        typer.Option("--machine-readable", "-mr", help="Should we just output json?"),
    ] = False,
):
    """Lists the agent lifecycle hooks: startup, shutdown and background.

    Startup hooks populate states/contexts when the agent starts; background
    workers run alongside it; shutdown hooks run on teardown. All are read from
    the app registry without connecting to a server.
    """
    console = get_console(ctx)
    app = load_app_or_exit(ctx, target)

    if app.registry.is_empty():
        cli_error(NOTHING_TO_PROVIDE)

    # The hooks the app would run: those declared on it. Read off the declaration,
    # not a snapshot: listing hooks needs no port validation.
    hooks_registry = app.registry.hooks_registry
    data = {
        "startup": _records(hooks_registry.startup_hooks),
        "shutdown": _records(hooks_registry.shutdown_hooks),
        "background": _records(hooks_registry.background_worker),
    }

    if machine_readable:
        emit_machine_readable("LIFECYCLE", data)
        return
    if pretty:
        console.print(json.dumps(data, indent=2))
        return

    tree = Tree("[bold]Lifecycle hooks[/]")
    for section, rows in data.items():
        branch = tree.add(f"[bold]{section}[/] ({len(rows)})")
        for row in rows:
            branch.add(f"{row['name']}  [dim]{row['module']}.{row['qualname']}[/dim]")
    console.print(tree)
