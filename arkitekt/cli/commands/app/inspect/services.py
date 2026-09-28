import json
from typing import Annotated, Any, Optional

import typer
from rich.console import Group
from rich.panel import Panel
from rich.table import Table

from arkitekt_spec.declare.service import Service

from arkitekt.cli.errors import cli_error
from arkitekt.cli.utils import emit_machine_readable
from arkitekt.cli.vars import get_console
from arkitekt.cli.commands.app.inspect.utils import run_snapshot_or_exit
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit


def _describe_service(name: str, svc: Service[Any]) -> dict[str, Any]:
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
    target: TargetArgument = DEFAULT_TARGET,
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

    Loads the target's app and reports each service it declares, its fakts requirements, and whether it
    ships a GraphQL schema / turms project for codegen — all without touching a
    server.
    """
    console = get_console(ctx)
    # The services a run of this app would build clients for: those it declares
    # (`App(services=[...])`, `app.service(...)`) and the one its provider brings
    # (rekuest's, when it offers something) -- not every one the process imported.
    service_builders = run_snapshot_or_exit(load_app_or_exit(ctx, target)).services

    if schema is not None:
        svc = service_builders.get(schema)
        if svc is None:
            cli_error(
                f"Unknown service '{schema}'. Available: "
                + ", ".join(service_builders.keys())
            )
        try:
            sdl = svc.get_graphql_schema()
        except Exception as e:
            cli_error(f"Service '{schema}' ships no GraphQL schema: {e}")
        print(sdl)
        return

    records = [
        _describe_service(name, svc)
        for name, svc in service_builders.items()
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
