from typing import Annotated
import typer

from arkitekt.cli.commands.app.inspect.utils import run_snapshot_or_exit
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.utils import emit_machine_readable
from arkitekt.cli.vars import get_console
import json


def requirements(
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
    """Checks the requirements of the app

    What a run of the app needs of a deployment: its services' requirements and
    those of the provider serving it, read off the declaration without connecting.
    """

    console = get_console(ctx)
    app = load_app_or_exit(ctx, target)

    requirements = run_snapshot_or_exit(app).manifest.requirements or []
    x = [item.model_dump(by_alias=True) for item in requirements]

    if machine_readable:
        emit_machine_readable("REQUIREMENTS", x)

    else:
        if pretty:
            console.print(json.dumps(x, indent=2))
        else:
            print(json.dumps(x))
