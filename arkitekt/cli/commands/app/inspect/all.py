from typing import Annotated
import typer

from arkitekt.app.spec import app_declaration
from arkitekt.cli.commands.app.inspect.utils import NOTHING_TO_PROVIDE, run_snapshot_or_exit
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.options import JsonOption, LogLevel, LogLevelOption, MachineReadableOption
from arkitekt.cli.utils import configure_logging, emit_machine_readable, json_stdout
from arkitekt.cli.vars import get_console
import json


def all(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    as_json: JsonOption = False,
    machine_readable: MachineReadableOption = False,
    log_level: LogLevelOption = LogLevel.ERROR,
):
    """Inspect everything this app exposes

    Loads the app without connecting it and reports its implementations, states,
    requirements, bloks and assets (each with its path in the app and its hash), as
    JSON: --json indents it, --machine-readable wraps it in markers for a program.
    """
    configure_logging(log_level.value)

    console = get_console(ctx)
    with json_stdout(as_json):
        app = load_app_or_exit(ctx, target)

    if app.registry.is_empty():
        console.print(NOTHING_TO_PROVIDE)
        return

    # What a run would serve, validated the way a run validates it, with the
    # requirements that run's provider adds.
    run = run_snapshot_or_exit(app)

    # The spec's Inspection, which the build on the host reads back with the same
    # model. The action language inside it is validated by rekuest on the way out.
    declaration = app_declaration(app, run, entrypoint=target)
    agent = declaration.to_inspection().model_dump(mode="json", by_alias=True, exclude_none=True)

    if machine_readable:
        emit_machine_readable("AGENT", agent)
        # Who the image says it is. `plugin release` holds this against the release
        # it is about to describe: the version a container registers under is the
        # one it carries, whatever the tag on it claims.
        # The declaration's manifest, scopes included the way a run asks for them (its
        # provider's services' too): a mandate key is pinned to it.
        emit_machine_readable("MANIFEST", declaration.manifest.model_dump(mode="json"))

    else:
        if as_json:
            print(json.dumps(agent, indent=2))
        else:
            print(json.dumps(agent))
