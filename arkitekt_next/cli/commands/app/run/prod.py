from typing import Annotated, Optional
import typer
from arkitekt_next.cli.commands.app.run.dev import resolve_entrypoint
from arkitekt_next.constants import DEFAULT_ARKITEKT_URL
from arkitekt_next.cli.vars import get_console, get_manifest
import asyncio
from arkitekt_next.cli.ui import construct_run_panel
from importlib import import_module
from .utils import import_builder, run_app, LogLevel
import sys


def prod(
    ctx: typer.Context,
    entrypoint: Annotated[Optional[str], typer.Argument()] = None,
    url: Annotated[
        str,
        typer.Option(
            "--url",
            "-u",
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
    redeem_token: Annotated[
        Optional[str],
        typer.Option(
            "--redeem-token",
            "-r",
            help="The redeem token used to authenticate against the fakts_next instance",
            envvar="FAKTS_REDEEM_TOKEN",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Force registration, kicking any existing connection for this agent and taking over",
            envvar="ARKITEKT_FORCE",
        ),
    ] = False,
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
    version: Annotated[
        Optional[str],
        typer.Option(
            "--version",
            "-v",
            help="Override the version of the app",
            envvar="ARKITEKT_VERSION",
        ),
    ] = None,
) -> None:
    """Runs the app in production mode

    \n
    You can specify the builder to use with the --builder flag. By default, the easy builder is used, which is designed to be easy to use and to get started with.

    """

    manifest = get_manifest(ctx)
    console = get_console(ctx)
    entrypoint = entrypoint or manifest.entrypoint

    builder = import_builder(builder)

    entrypoint_module, entrypoint_file = resolve_entrypoint(entrypoint)

    with console.status("Loading entrypoint module..."):
        try:
            import_module(entrypoint_module)
        except ModuleNotFoundError as e:
            console.print(f"Could not find entrypoint module {entrypoint_module}")
            raise e

    builder_kwargs = {
        "url": url,
        "token": token,
        "redeem_token": redeem_token,
        "force": force,
        "headless": headless,
        "log_level": log_level.value,
        "no_cache": no_cache,
    }

    # Build from the manifest; let --version override the manifest version if given.
    builder_args = {**manifest.to_builder_dict(), **builder_kwargs}
    if version:
        builder_args["version"] = version

    app = builder(**builder_args)

    panel = construct_run_panel(app)
    console.print(panel)

    try:
        asyncio.run(run_app(app))
    except Exception as e:
        console.print_exception()
        sys.exit(1)
