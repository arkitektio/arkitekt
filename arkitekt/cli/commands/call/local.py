import rich_click as click
from arkitekt.cli.options import *
import asyncio
from arkitekt.cli.ui import construct_run_panel
from importlib import import_module
from rekuest.postmans.utils import arkiuse
from arkitekt.cli.utils import import_builder
from rekuest.api.schema import (
    NodeKind,
    ReserveBindsInput,
)
from rich.table import Table
from rich.console import Console
from typing import Dict, Any


async def call_app(
    console: Console,
    app: App,
    template_string: str,
    arg: Dict[str, Any],
):
    async with app:
        await app.rekuest.agent.aregister_definitions()

        run_task = asyncio.create_task(app.rekuest.run())

        template = app.rekuest.agent.interface_template_map[template_string]

        async with arkiuse(
            hash=template.node.hash,
            binds=ReserveBindsInput(templates=[template.id], clients=[]),
            postman=app.rekuest.postman,
        ) as a:
            if template.node.kind == NodeKind.GENERATOR:
                async for i in a.astream(kwargs=arg):
                    table = Table(title=f"Yields of {template.node.name}")
                    table.add_column("key")
                    table.add_column("value")

                    for key, value in i.items():
                        table.add_row(key, value)

                    console.print(table)

            else:
                i = await a.aassign(kwargs=arg)
                table = Table(title=f"Returns of {template.node.name}")
                table.add_column("key")
                table.add_column("value")

                for key, value in i.items():
                    table.add_row(key, value)

                console.print(table)

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
    "--template",
    "-t",
    "template",
    help="The template to run",
    type=str,
)
def local(
    ctx,
    entrypoint=None,
    builder=None,
    args=None,
    template: str = None,
    **builder_kwargs,
):
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

    asyncio.run(call_app(console, app, template, kwargs))
