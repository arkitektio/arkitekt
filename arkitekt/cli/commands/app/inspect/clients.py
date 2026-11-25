import json
from typing import Annotated, Any

import typer
from arkitekt_spec.declare.client import ClientDeclaration
from rich.console import Group
from rich.padding import Padding
from rich.table import Table

from arkitekt.cli.commands.app.inspect.utils import run_snapshot_or_exit
from arkitekt.cli.errors import cli_error
from arkitekt.cli.options import (
    JsonOption,
    LogLevel,
    LogLevelOption,
    MachineReadableOption,
)
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.ui import construct_section
from arkitekt.cli.utils import configure_logging, emit_machine_readable, json_stdout
from arkitekt.cli.vars import get_console


def _describe_client(name: str, svc: ClientDeclaration[Any]) -> dict[str, Any]:
    """Project one client into a JSON-friendly record."""
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
        "class": f"{svc.cls.__module__}.{svc.cls.__qualname__}",
        "image": svc.image,
        "requirements": [r.model_dump(by_alias=True) for r in svc.get_requirements()],
        "has_schema": schema is not None,
        "schema_bytes": len(schema) if schema is not None else 0,
        "has_turms_project": turms_project is not None,
    }


def clients(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    schema: Annotated[
        str | None,
        typer.Option(
            "--schema",
            help="Print the raw GraphQL SDL of this one client and exit.",
        ),
    ] = None,
    as_json: JsonOption = False,
    machine_readable: MachineReadableOption = False,
    log_level: LogLevelOption = LogLevel.ERROR,
) -> None:
    """List the clients a run of this app would build or be handed.

    Reports each client's requirements and whether it ships a GraphQL schema /
    turms project for codegen, without touching a server.
    """
    configure_logging(log_level.value)
    console = get_console(ctx)
    # The clients a run would build: those the app uses, and those its provider
    # brings (rekuest's, when it offers something).
    with json_stdout(as_json):
        declared = run_snapshot_or_exit(load_app_or_exit(ctx, target)).clients

    if schema is not None:
        svc = declared.get(schema)
        if svc is None:
            cli_error(f"Unknown client '{schema}'. Available: " + ", ".join(declared))
        try:
            sdl = svc.get_graphql_schema()
        except Exception as e:
            cli_error(f"Client '{schema}' ships no GraphQL schema: {e}")
        # Bytes: a pipe on Windows would encode text as cp1252, and a schema is UTF-8.
        typer.echo((sdl or "").encode("utf-8"))
        return

    records = [_describe_client(name, svc) for name, svc in declared.items()]

    if machine_readable:
        emit_machine_readable("CLIENTS", records)
        return
    if as_json:
        print(json.dumps(records, indent=2))
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
        table.add_row("Image", record["image"] or "-")
        table.add_row("GraphQL schema", "yes" if record["has_schema"] else "no")
        table.add_row("Turms project", "yes" if record["has_turms_project"] else "no")
        renderables.append(
            Group(f"[bold cyan]{record['name']}[/]", Padding(table, (0, 0, 1, 2)))
        )

    console.print(construct_section("Clients", Group(*renderables)))
