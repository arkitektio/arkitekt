from importlib import import_module
import json
from typing import Annotated

import typer
from rich.panel import Panel
from rich.tree import Tree

from arkitekt.cli.errors import cli_error
from arkitekt.cli.utils import emit_machine_readable
from arkitekt.cli.vars import get_console, get_manifest
from rekuest.app import get_default_app_registry


def _records(hooks: dict) -> list:
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
    manifest = get_manifest(ctx)

    with console.status("Loading entrypoint module..."):
        try:
            import_module(manifest.entrypoint)
        except ModuleNotFoundError as e:
            cli_error(f"Could not import entrypoint module '{manifest.entrypoint}': {e}")

    hooks_registry = get_default_app_registry().hooks_registry
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

    tree = Tree("Lifecycle hooks")
    for section, rows in data.items():
        branch = tree.add(f"[bold]{section}[/] ({len(rows)})")
        for row in rows:
            branch.add(f"{row['name']}  [dim]{row['module']}.{row['qualname']}[/dim]")
    console.print(Panel(tree, border_style="green"))
