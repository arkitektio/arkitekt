from typing import Annotated
import typer

from arkitekt.cli.commands.app.inspect.utils import run_snapshot_or_exit
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.options import JsonOption, LogLevel, LogLevelOption, MachineReadableOption
from arkitekt.cli.utils import configure_logging, emit_machine_readable, json_stdout
from arkitekt.cli.vars import get_console
import json


def requirements(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    as_json: JsonOption = False,
    machine_readable: MachineReadableOption = False,
    log_level: LogLevelOption = LogLevel.ERROR,
):
    """List what the app requires of a deployment

    What a run of the app needs of a deployment: its services' requirements and
    those of the provider serving it, read off the declaration without connecting.
    """
    configure_logging(log_level.value)

    console = get_console(ctx)
    with json_stdout(as_json):
        app = load_app_or_exit(ctx, target)

    requirements = run_snapshot_or_exit(app).manifest.requirements or []
    x = [item.model_dump(by_alias=True) for item in requirements]

    if machine_readable:
        emit_machine_readable("REQUIREMENTS", x)

    else:
        if as_json:
            print(json.dumps(x, indent=2))
        else:
            print(json.dumps(x))
