import asyncio
from typing import Annotated
from pydantic import BaseModel
import typer

from arkitekt.cli.utils import emit_machine_readable
from importlib import import_module
from arkitekt.app.app import App
from arkitekt.cli.commands.app.run.utils import import_builder
from arkitekt.cli.vars import get_console, get_manifest
import json
import os

from arkitekt.constants import DEFAULT_ARKITEKT_URL
from arkitekt.service_registry import get_default_service_registry
from rekuest.app import get_default_app_registry

try:
    from rekuest.definition.registry import get_default_definition_registry
except ImportError:
    get_default_definition_registry = lambda: None
    pass


def all(
    ctx: typer.Context,
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

    Builds the app without running it and reports its variables, requirements and
    implementations. Pass --machine-readable to get JSON instead of a table.
    """
    builder: str = "arkitekt.builders.easy"
    url: str = DEFAULT_ARKITEKT_URL

    manifest = get_manifest(ctx)
    console = get_console(ctx)

    entrypoint = manifest.entrypoint
    identifier = manifest.identifier
    entrypoint_file = f"{manifest.entrypoint}.py"
    os.path.realpath(entrypoint_file)

    builder_func = import_builder(builder)

    entrypoint = manifest.entrypoint

    with console.status("Loading entrypoint module..."):
        try:
            import_module(entrypoint)
        except ModuleNotFoundError as e:
            console.print(f"Could not find entrypoint module {entrypoint}")
            raise e

    app: App = builder_func(
        identifier=identifier,
        version="dev",
        logo=manifest.logo,
        url=url,
        headless=True,
    )

    rekuest = app.services.get("rekuest")

    registry = get_default_app_registry()

    service_registry = get_default_service_registry()

    x = [item.model_dump(by_alias=True) for item in service_registry.get_requirements()]

    # Assemble the agent payload through ImplementAgentInput so it is validated
    # the same way the server would validate it, instead of hand-rolling raw
    # model_dump()s. `name`/`hash` are agent-instance concerns, and requirements
    # are a fakts/manifest concept, so they stay out of / get added to the dump.
    agent_input = registry.to_implement_agent_input()
    agent = {
        **agent_input.model_dump(exclude={"name", "hash"}),
        "requirements": x,
    }

    if rekuest is None:
        console.print("No rekuest service found in app")
        return

    if machine_readable:
        emit_machine_readable("AGENT", agent)

    else:
        if pretty:
            console.print(json.dumps(agent, indent=2))
        else:
            print(json.dumps(agent))
