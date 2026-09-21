import json
from typing import Annotated, Any

import typer
from rich.table import Table

from arkitekt.cli.commands.app.inspect.utils import snapshot_or_exit
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.utils import emit_machine_readable
from arkitekt.cli.vars import get_console


def _widget_name(widget: Any) -> str | None:
    """`SearchAssignWidgetInput` -> `search`: widgets are one class per kind."""
    if widget is None:
        return None
    return type(widget).__name__.removesuffix("AssignWidgetInput").lower() or None


def _describe_structure(structure: Any, used_by: dict[str, set[str]]) -> dict:
    """Project one structure into a JSON-friendly record."""
    cls = structure.cls
    widget = structure.default_widget
    return {
        "identifier": structure.identifier,
        "service": structure.service,
        "class": f"{cls.__module__}.{cls.__qualname__}",
        "widget": _widget_name(widget),
        "batched": structure.aexpand_many is not None,
        "used_by": sorted(used_by.get(structure.identifier, ())),
    }


def _interfaces_by_identifier(registry: Any) -> dict[str, set[str]]:
    """Which registered functions take or return each structure."""
    used: dict[str, set[str]] = {}

    def visit(interface: str, ports: Any) -> None:
        for port in ports or ():
            if port.identifier:
                used.setdefault(port.identifier, set()).add(interface)
            visit(interface, port.children)

    for implementation in registry.get_implementations():
        interface = implementation.interface or implementation.definition.name
        visit(interface, implementation.definition.args)
        visit(interface, implementation.definition.returns)
    return used


def structures(
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
    """Lists the structures this app can send and receive by id.

    A structure belongs to the service that declares it, so this is a function
    of the app's services: what the App declares is what shows up here. The class
    each identifier names is in --machine-readable, not the table, where it only
    repeats the identifier. Loads the app without connecting it, and touches no
    server.
    """

    console = get_console(ctx)
    app = load_app_or_exit(ctx, target)

    # What a run would serve: the app's structures and its provider's.
    registry = snapshot_or_exit(app)
    used_by = _interfaces_by_identifier(registry)
    records = [
        _describe_structure(structure, used_by)
        for structure in registry.structure_registry.structures()
    ]

    if machine_readable:
        emit_machine_readable("STRUCTURES", records)
        return
    if pretty:
        console.print(json.dumps(records, indent=2))
        return

    table = Table(title=f"Structures ({len(records)})", border_style="green")
    table.add_column("Identifier", style="bold green", no_wrap=True)
    table.add_column("Service", no_wrap=True)
    table.add_column("Widget", no_wrap=True)
    table.add_column("Used by")
    for record in records:
        table.add_row(
            record["identifier"],
            record["service"] or "[red]none[/]",
            record["widget"] or "-",
            ", ".join(record["used_by"]) or "-",
        )
    console.print(table)
