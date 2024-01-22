import rich_click as click
from arkitekt.cli.options import *
import asyncio
from arkitekt.cli.ui import construct_run_panel
from importlib import import_module
from rekuest.postmans.utils import arkiuse
import rich_click as click
from arkitekt.cli.options import *
import asyncio
from arkitekt.cli.ui import construct_run_panel
from importlib import import_module
from arkitekt.cli.utils import import_builder


async def call_app(
    app: App,
    hash,
    arg,
):
    async with app:
        run_task = asyncio.create_task(app.rekuest.run())

        app.rekuest.agent.definition_registry.definitions

        async with arkiuse(
            hash=hash,
            postman=app.rekuest.postman,
        ) as a:
            print(arg)
            print(await a.aassign(kwargs=arg))

        run_task.cancel()

        try:
            await run_task
        except asyncio.CancelledError:
            pass


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
@with_skip_cache
@click.pass_context
@click.option(
    "--arg",
    "-a",
    "args",
    help="Key Value pairs for the setup",
    type=(str, str),
    multiple=True,
)
@click.option(
    "--hash",
    "-h",
    help="The hash of the node to run",
    type=str,
)
def remote(ctx, entrypoint=None, builder=None, args=None, hash=str, **builder_kwargs):
    """Runs the app in production mode

    \n
    You can specify the builder to use with the --builder flag. By default, the easy builder is used, which is designed to be easy to use and to get started with.

    """

    manifest = get_manifest(ctx)
    console = get_console(ctx)
    entrypoint = entrypoint or manifest.entrypoint

    kwargs = dict(args or [])

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

    asyncio.run(call_app(app, hash, kwargs))
