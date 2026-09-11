from typing import Annotated
from arkitekt_next import get_default_service_registry
import typer

from arkitekt_next.cli.utils import emit_machine_readable
from importlib import import_module
from arkitekt_next.app.app import App
from arkitekt_next.cli.commands.app.run.utils import import_builder
from arkitekt_next.cli.vars import get_console, get_manifest
import json
import os


async def run_app(app):
    async with app:
        await app.rekuest.run()


def requirements(
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
    """Checks the requirements of the app

    \n
    """

    manifest = get_manifest(ctx)
    console = get_console(ctx)

    entrypoint = manifest.entrypoint
    identifier = manifest.identifier
    entrypoint_file = f"{manifest.entrypoint}.py"
    os.path.realpath(entrypoint_file)

    entrypoint = manifest.entrypoint

    with console.status("Loading entrypoint module..."):
        try:
            import_module(entrypoint)
        except ModuleNotFoundError as e:
            console.print(f"Could not find entrypoint module {entrypoint}")
            raise e

    service_registry = get_default_service_registry()

    x = [item.model_dump(by_alias=True) for item in service_registry.get_requirements()]

    if machine_readable:
        emit_machine_readable("REQUIREMENTS", x)

    else:
        if pretty:
            console.print(json.dumps(x, indent=2))
        else:
            print(json.dumps(x))
