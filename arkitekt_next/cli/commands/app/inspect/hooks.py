from importlib import import_module
import json
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from arkitekt_next.cli.errors import cli_error
from arkitekt_next.cli.utils import emit_machine_readable
from arkitekt_next.cli.vars import get_console, get_manifest
from arkitekt_next.init_registry import get_default_init_hook_registry


def _hook_record(name: str, fn: object, cli_only: bool, order: int) -> dict:
    doc = (getattr(fn, "__doc__", None) or "").strip().splitlines()
    return {
        "name": name,
        "module": getattr(fn, "__module__", ""),
        "qualname": getattr(fn, "__qualname__", ""),
        "doc": doc[0] if doc else "",
        "cli_only": cli_only,
        "order": order,
    }


def hooks(
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
    """Lists this app's @init hooks in the order they run.

    Init hooks run right after the app is built, before it connects. CLI-only
    hooks additionally run only when the app is started through the CLI.
    """
    console = get_console(ctx)
    manifest = get_manifest(ctx)

    with console.status("Loading entrypoint module..."):
        try:
            import_module(manifest.entrypoint)
        except ModuleNotFoundError as e:
            cli_error(f"Could not import entrypoint module '{manifest.entrypoint}': {e}")

    registry = get_default_init_hook_registry()

    records = [
        _hook_record(name, fn, cli_only=False, order=i)
        for i, (name, fn) in enumerate(registry.init_hooks.items())
    ]
    offset = len(records)
    records += [
        _hook_record(name, fn, cli_only=True, order=offset + i)
        for i, (name, fn) in enumerate(registry.cli_only_hooks.items())
    ]

    if machine_readable:
        emit_machine_readable("HOOKS", records)
        return
    if pretty:
        console.print(json.dumps(records, indent=2))
        return

    if not records:
        console.print("No init hooks registered.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("#")
    table.add_column("Name")
    table.add_column("Module")
    table.add_column("CLI only")
    table.add_column("Doc")
    for record in records:
        table.add_row(
            str(record["order"]),
            record["name"],
            record["module"],
            "yes" if record["cli_only"] else "",
            record["doc"],
        )
    console.print(Panel(table, title="Init hooks", border_style="green"))
