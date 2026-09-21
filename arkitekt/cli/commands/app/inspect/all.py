from typing import Annotated
import typer

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
    registry = run.registry

    # Assemble the agent payload through ImplementAgentInput so it is validated
    # the same way the server would validate it, instead of hand-rolling raw
    # model_dump()s. `name`/`hash` are agent-instance concerns, and requirements
    # are a fakts/manifest concept, so they stay out of / get added to the dump.
    agent_input = registry.to_implement_agent_input()
    agent = {
        **agent_input.model_dump(exclude={"name", "hash"}),
        "requirements": [item.model_dump(by_alias=True) for item in run.manifest.requirements],
    }

    if machine_readable:
        emit_machine_readable("AGENT", agent)

    else:
        if pretty:
            console.print(json.dumps(agent, indent=2))
        else:
            print(json.dumps(agent))
