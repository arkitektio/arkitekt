from typing import Annotated
import typer

from arkitekt.cli.commands.app.inspect.utils import NOTHING_TO_PROVIDE, snapshot_or_exit
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.utils import emit_machine_readable
from arkitekt.cli.vars import get_console
import json


def implementations(
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
    """Inspect the implementations this app registers.

    Loads the app without connecting it and lists the implementations it would
    register. Pass --machine-readable to get JSON instead of a table.
    """

    console = get_console(ctx)
    app = load_app_or_exit(ctx, target)

    if app.registry.is_empty():
        console.print(NOTHING_TO_PROVIDE)
        return

    # What a run would serve: the validated snapshot of what was declared.
    global_list = [d.model_dump() for d in snapshot_or_exit(app).get_implementations()]

    console.print(f"Implementations to be created: {len(global_list)}")

    if machine_readable:
        emit_machine_readable("TEMPLATES", global_list)

    else:
        if pretty:
            console.print(json.dumps(global_list, indent=2))
        else:
            print(json.dumps(global_list))
