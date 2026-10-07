from typing import Annotated
import typer

from arkitekt.app.spec import app_inspection, app_manifest
from arkitekt.cli.commands.app.inspect.utils import NOTHING_TO_PROVIDE, run_snapshot_or_exit
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.utils import emit_machine_readable
from arkitekt.cli.vars import get_console
import json


def all(
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
    """Inspect everything this app exposes.

    Loads the app without connecting it and reports its implementations, states,
    requirements and bloks. Pass --machine-readable to get JSON instead of a table.
    """

    console = get_console(ctx)
    app = load_app_or_exit(ctx, target)

    if app.registry.is_empty():
        console.print(NOTHING_TO_PROVIDE)
        return

    # What a run would serve, validated the way a run validates it, with the
    # requirements that run's provider adds.
    run = run_snapshot_or_exit(app)

    # The spec's Inspection, which the build on the host reads back with the same
    # model. The action language inside it is validated by rekuest on the way out.
    agent = app_inspection(app, run).model_dump(mode="json", by_alias=True, exclude_none=True)

    if machine_readable:
        emit_machine_readable("AGENT", agent)
        # Who the image says it is. `plugin release` holds this against the release
        # it is about to describe: the version a container registers under is the
        # one it carries, whatever the tag on it claims.
        emit_machine_readable(
            "MANIFEST", app_manifest(app, entrypoint=target).model_dump(mode="json")
        )

    else:
        if pretty:
            console.print(json.dumps(agent, indent=2))
        else:
            print(json.dumps(agent))
