from typing import Annotated, Optional
import typer
import asyncio
from arkitekt_next.app.app import App
from arkitekt_next.cli.ui import construct_run_panel
from arkitekt_next.cli.vars import get_console, get_manifest
from importlib import import_module
from .utils import import_builder, LogLevel
from arkitekt_next.constants import DEFAULT_ARKITEKT_URL
import sys


async def run_tests(app: App):
    rekuest = app.rekuest




    async with app:

        x = asyncio.create_task(rekuest.arun())





def tests(
    ctx: typer.Context,
    url: Annotated[
        str,
        typer.Option(
            "--url",
            help="The fakts url for connection",
            envvar="FAKTS_URL",
        ),
    ] = DEFAULT_ARKITEKT_URL,
    builder: Annotated[
        str,
        typer.Option(
            "--builder",
            "-b",
            help="The builder for this run",
            envvar="ARKITEKT_BUILDER",
        ),
    ] = "arkitekt_next.builders.easy",
    token: Annotated[
        Optional[str],
        typer.Option(
            "--token",
            "-t",
            help="The token for the fakts_next instance",
            envvar="FAKTS_TOKEN",
        ),
    ] = None,
    redeem_token: Annotated[
        Optional[str],
        typer.Option(
            "--redeem-token",
            "-r",
            help="The redeem token used to authenticate against the fakts_next instance",
            envvar="FAKTS_REDEEM_TOKEN",
        ),
    ] = None,
    headless: Annotated[
        bool,
        typer.Option(
            "--headless",
            help="Should we start headless",
            envvar="ARKITEKT_HEADLESS",
        ),
    ] = False,
    log_level: Annotated[
        LogLevel,
        typer.Option(
            "--log-level",
            "-l",
            help="The logging level to use",
            envvar="ARKITEKT_LOG_LEVEL",
        ),
    ] = LogLevel.ERROR,
    no_cache: Annotated[
        bool,
        typer.Option(
            "--no-cache",
            "-nc",
            help="Should we skip the cache",
            envvar="ARKITEKT_NO_CACHE",
        ),
    ] = False,
) -> None:
    """Runs the app in production mode

    \n
    You can specify the builder to use with the --builder flag. By default, the easy builder is used, which is designed to be easy to use and to get started with.

    """

    manifest = get_manifest(ctx)
    console = get_console(ctx)
    entrypoint = manifest.entrypoint

    builder = import_builder(builder)

    with console.status("Loading entrypoint module..."):
        try:
            import_module(entrypoint)
        except ModuleNotFoundError as e:
            console.print(f"Could not find entrypoint module {entrypoint}")
            raise e

    builder_kwargs = {
        "url": url,
        "token": token,
        "redeem_token": redeem_token,
        "headless": headless,
        "log_level": log_level.value,
        "no_cache": no_cache,
    }

    app = builder(
        **manifest.to_builder_dict(),
        **builder_kwargs,
    )

    panel = construct_run_panel(app)
    console.print(panel)

    try:
        asyncio.run(run_tests(app))
    except Exception as e:
        console.print_exception()
        sys.exit(1)
