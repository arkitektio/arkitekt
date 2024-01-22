import rich_click as click
from importlib import import_module
from arkitekt.cli.vars import get_console, get_manifest
from arkitekt.cli.options import with_builder
import json


async def run_app(app):
    async with app:
        await app.rekuest.run()


@click.command("prod")
@click.pass_context
@click.option(
    "--pretty",
    "-p",
    help="Should we just output json?",
    is_flag=True,
    default=False,
)
@with_builder
def definitions(
    ctx,
    pretty: bool,
    builder=None,
):
    """Runs the app in production mode

    \n
    You can specify the builder to use with the --builder flag. By default, the easy builder is used, which is designed to be easy to use and to get started with.

    """
    from rekuest.definition.registry import get_default_definition_registry

    manifest = get_manifest(ctx)
    console = get_console(ctx)

    entrypoint = manifest.entrypoint

    with console.status("Loading entrypoint module..."):
        try:
            import_module(entrypoint)
        except ModuleNotFoundError as e:
            console.print(f"Could not find entrypoint module {entrypoint}")
            raise e

    definitions = get_default_definition_registry().dump()

    if pretty:
        console.print(json.dumps(definitions, indent=2))
    else:
        print(json.dumps(definitions))
