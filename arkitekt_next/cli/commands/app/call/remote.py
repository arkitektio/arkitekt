from enum import Enum
from typing import Annotated, List, Optional
import typer
from arkitekt_next.cli.vars import get_console, get_manifest
import asyncio
from arkitekt_next.cli.ui import construct_run_panel
from importlib import import_module
from arkitekt_next.app import App
from arkitekt_next.cli.ui import construct_run_panel
from importlib import import_module
from arkitekt_next.cli.utils import import_builder
from arkitekt_next.constants import DEFAULT_ARKITEKT_URL


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


async def call_app(
    app: App,
    hash,
    arg,
):
    async with app:
        raise NotImplementedError("This is not implemented yet")


def remote(
    ctx: typer.Context,
    url: Annotated[
        str,
        typer.Option(
            "--url",
            help="The fakts_next url for connection",
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
            "-h",
            help="The hash of the node to run",
        ),
    ] = None,
):
    """ALlows you to run a get the output of a node in a remote app.

    This is useful for debugging and testing. In this mode the app itself will not
    be run, so local nodes cannot be called. Only nodes that are availabble on your
    arkitekt_next server can be called.

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
