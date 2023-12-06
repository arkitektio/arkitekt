import rich_click as click
from arkitekt.cli.options import *
import asyncio
from arkitekt.cli.ui import construct_run_panel
from importlib import import_module
from .utils import import_builder


async def run_app(app):
    async with app:
        await app.rekuest.run()


@click.command("prod")
@click.option(
    "--url",
    help="The fakts url for connection",
    default="http://localhost:8000",
    envvar="FAKTS_URL",
)
@with_builder
@with_token
@with_instance_id
@with_headless
@with_log_level
@with_version
@with_skip_cache
@click.pass_context
def prod(ctx, version=None, url=None, entrypoint=None, builder=None, **builder_kwargs):
    """Runs the app in production mode

    \n
    You can specify the builder to use with the --builder flag. By default, the easy builder is used, which is designed to be easy to use and to get started with.

    """

    manifest = get_manifest(ctx)
    console = get_console(ctx)
    entrypoint = entrypoint or manifest.entrypoint

    builder = import_builder(builder)

    with console.status("Loading entrypoint module..."):
        try:
            import_module(entrypoint)
        except ModuleNotFoundError as e:
            console.print(f"Could not find entrypoint module {entrypoint}")
            raise e

    app = builder(
        **manifest.to_builder_dict(),
        **builder_kwargs,
    )

    panel = construct_run_panel(app)
    console.print(panel)

    asyncio.run(run_app(app))
