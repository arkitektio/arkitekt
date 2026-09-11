from importlib import import_module
import json
from typing import Annotated, Optional

import typer
from rich.console import Group
from rich.panel import Panel
from rich.table import Table

from arkitekt.cli.errors import cli_error
from arkitekt.cli.utils import emit_machine_readable
from arkitekt.cli.vars import get_console, get_manifest
from arkitekt.service_registry import get_default_service_registry


def _describe_service(name: str, svc: object) -> dict:
    """Project one registered service into a JSON-friendly record."""
    schema = None
    turms_project = None
    try:
        schema = svc.get_graphql_schema()
    except Exception:
        pass
    try:
        turms_project = svc.get_turms_project()
    except Exception:
        pass

    return {
        "name": name,
        "class": f"{type(svc).__module__}.{type(svc).__qualname__}",
        "requirements": [
            r.model_dump(by_alias=True) for r in svc.get_requirements()
        ],
        "has_schema": schema is not None,
        "schema_bytes": len(schema) if schema is not None else 0,
        "has_turms_project": turms_project is not None,
    }


def services(
    ctx: typer.Context,
    schema: Annotated[
        Optional[str],
        typer.Option(
            "--schema",
            help="Print the raw GraphQL SDL of this one service and exit.",
        ),
    ] = None,
    pretty: Annotated[
        bool,
        typer.Option("--pretty", "-p", help="Should we just output json?"),
    ] = False,
    machine_readable: Annotated[
        bool,
        typer.Option("--machine-readable", "-mr", help="Should we just output json?"),
    ] = False,
):
    """Lists the service SDKs this app would connect through.

    Imports the entrypoint (which registers the installed service packages) and
    reports each registered service, its fakts requirements, and whether it
    ships a GraphQL schema / turms project for codegen — all without touching a
    server.
    """
    console = get_console(ctx)
    manifest = get_manifest(ctx)

    with console.status("Loading entrypoint module..."):
        try:
            import_module(manifest.entrypoint)
        except ModuleNotFoundError as e:
            cli_error(f"Could not import entrypoint module '{manifest.entrypoint}': {e}")

    registry = get_default_service_registry()

    if schema is not None:
        svc = registry.service_builders.get(schema)
        if svc is None:
            cli_error(
                f"Unknown service '{schema}'. Available: "
                + ", ".join(registry.service_builders.keys())
            )
        try:
            sdl = svc.get_graphql_schema()
        except Exception as e:
            cli_error(f"Service '{schema}' ships no GraphQL schema: {e}")
        print(sdl)
        return

    records = [
        _describe_service(name, svc)
        for name, svc in registry.service_builders.items()
    ]

    if machine_readable:
        emit_machine_readable("SERVICES", records)
        return
    if pretty:
        console.print(json.dumps(records, indent=2))
        return

    renderables = []
    for record in records:
        table = Table.grid(padding=(0, 3))
        table.add_column()
        table.add_column()
        table.add_row("Class", record["class"])
        table.add_row(
            "Requirements",
            ", ".join(r["key"] for r in record["requirements"]) or "-",
        )
        table.add_row("GraphQL schema", "yes" if record["has_schema"] else "no")
        table.add_row("Turms project", "yes" if record["has_turms_project"] else "no")
        renderables.append(Group(f"[bold green]{record['name']}[/]", table))

    console.print(
        Panel(
            Group(*renderables),
            title="Registered services",
            border_style="green",
            style="white",
        )
    )
