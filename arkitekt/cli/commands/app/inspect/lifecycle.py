import json
from typing import Annotated, Any

import typer
from rich.tree import Tree

from arkitekt.cli.commands.app.inspect.utils import NOTHING_TO_PROVIDE
from arkitekt.cli.errors import cli_error
from arkitekt.cli.options import JsonOption, LogLevel, LogLevelOption, MachineReadableOption
from arkitekt.cli.utils import configure_logging, emit_machine_readable, json_stdout
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
    as_json: JsonOption = False,
    machine_readable: MachineReadableOption = False,
    log_level: LogLevelOption = LogLevel.ERROR,
):
    """List the agent lifecycle hooks: startup, shutdown and background

    Startup hooks populate states/contexts when the agent starts (a ``@app.lifecycle``
    hook is listed among them, as it runs among them); background
    workers run alongside it; shutdown hooks run on teardown. All are read from
    the app registry without connecting to a server.
    """
    configure_logging(log_level.value)
    console = get_console(ctx)
    with json_stdout(as_json):
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
    if as_json:
        print(json.dumps(data, indent=2))
        return

    tree = Tree("[bold]Lifecycle hooks[/]")
    for section, rows in data.items():
        branch = tree.add(f"[bold]{section}[/] ({len(rows)})")
        for row in rows:
            branch.add(f"{row['name']}  [dim]{row['module']}.{row['qualname']}[/dim]")
    console.print(tree)
