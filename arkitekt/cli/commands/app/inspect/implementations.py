import json
from typing import Annotated, Any

import typer
from rich.table import Table

from arkitekt.cli.commands.app.inspect.utils import NOTHING_TO_PROVIDE, snapshot_or_exit
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.utils import emit_machine_readable
from arkitekt.cli.vars import get_console


def _ports(ports: Any) -> str:  # noqa: ANN401
    """Ports as one line: ``a: INT, b: INT?``."""
    return ", ".join(
        f"{port.key}: {getattr(port.kind, 'value', port.kind)}{'?' if port.nullable else ''}"
        for port in ports
    )


def implementations_table(implementations: Any) -> Table:  # noqa: ANN401
    """The actions an app offers: what to call them by, and what they take and return."""
    from arkitekt_spec import definition_hash

    table = Table(box=None, pad_edge=False, padding=(0, 3, 0, 0), header_style="dim")
    for column in ("action", "takes", "returns", "hash"):
        table.add_column(column, overflow="fold")
    for implementation in implementations:
        definition = implementation.definition
        table.add_row(
            implementation.interface or definition.name,
            _ports(definition.args) or "-",
            _ports(definition.returns) or "-",
            definition_hash(definition)[:12],
        )
    return table


def implementations(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    as_json: Annotated[
        bool,
        typer.Option("--json", "-j", help="Print the full implementations as JSON."),
    ] = False,
    machine_readable: Annotated[
        bool,
        typer.Option(
            "--machine-readable", "-mr", help="Print the JSON between markers, for a program to read."
        ),
    ] = False,
):
    """Inspect the actions this app offers.

    Loads the app without connecting it and lists what it would register: each
    action by the name `arkitekt call local` takes, with its arguments, its
    results and the start of the hash it is found by on a server. Pass --json for
    everything.
    """

    console = get_console(ctx)
    app = load_app_or_exit(ctx, target)

    if app.registry.is_empty():
        console.print(NOTHING_TO_PROVIDE)
        return

    # What a run would serve: the validated snapshot of what was declared.
    declared = snapshot_or_exit(app).get_implementations()
    global_list = [d.model_dump() for d in declared]

    if machine_readable:
        console.print(f"Implementations to be created: {len(global_list)}")
        emit_machine_readable("TEMPLATES", global_list)
    elif as_json:
        print(json.dumps(global_list, indent=2))
    else:
        console.print(implementations_table(declared))
