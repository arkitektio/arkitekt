import asyncio
from importlib import import_module
from typing import Annotated, List, Optional

import typer

from arkitekt.app import App
from arkitekt.cli.options import (
    LogLevel,
    UrlOption,
    BuilderOption,
    TokenOption,
    HeadlessOption,
    LogLevelOption,
    NoCacheOption,
)
from arkitekt.cli.ui import construct_run_panel
from arkitekt.cli.utils import import_builder
from arkitekt.cli.vars import get_console, get_manifest
from arkitekt.constants import DEFAULT_ARKITEKT_URL


async def call_app(
    app: App,
    hash,
    arg,
):
    async with app:
        raise NotImplementedError("This is not implemented yet")


def remote(
    ctx: typer.Context,
    url: UrlOption = DEFAULT_ARKITEKT_URL,
    builder: BuilderOption = "arkitekt.builders.easy",
    token: TokenOption = None,
    headless: HeadlessOption = False,
    log_level: LogLevelOption = LogLevel.ERROR,
    no_cache: NoCacheOption = False,
    args: Annotated[
        List[str],
        typer.Option(
            "--arg",
            "-a",
            help="Key Value pairs for the setup",
        ),
    ] = [],
    hash: Annotated[
        Optional[str],
        typer.Option(
            "--hash",
            help="The hash of the node to run",
        ),
    ] = None,
):
    """Call a node in a remote app and print its output.

    This is useful for debugging and testing. In this mode the app itself will not
    be run, so local nodes cannot be called. Only nodes that are available on your
    arkitekt server can be called.

    """

    manifest = get_manifest(ctx)
    console = get_console(ctx)
    entrypoint = manifest.entrypoint

    kwargs = dict(args or [])

    builder_kwargs = {
        "url": url,
        "token": token,
        "headless": headless,
        "log_level": log_level.value,
        "no_cache": no_cache,
    }

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
