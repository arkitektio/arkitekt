from typing import Annotated, Optional
import typer
from arkitekt_next.cli.commands.app.run.dev import resolve_entrypoint
from arkitekt_next.constants import DEFAULT_ARKITEKT_URL
from arkitekt_next.cli.vars import get_console, get_manifest
import asyncio
from arkitekt_next.cli.ui import construct_run_panel
from importlib import import_module
from .utils import import_builder, run_app
from arkitekt_next.cli.options import (
    LogLevel,
    UrlOption,
    BuilderOption,
    TokenOption,
    RedeemTokenOption,
    ForceOption,
    HeadlessOption,
    LogLevelOption,
    NoCacheOption,
    VersionOption,
)
import sys


def prod(
    ctx: typer.Context,
    entrypoint: Annotated[Optional[str], typer.Argument()] = None,
    url: UrlOption = DEFAULT_ARKITEKT_URL,
    builder: BuilderOption = "arkitekt_next.builders.easy",
    token: TokenOption = None,
    redeem_token: RedeemTokenOption = None,
    force: ForceOption = False,
    headless: HeadlessOption = False,
    log_level: LogLevelOption = LogLevel.ERROR,
    no_cache: NoCacheOption = False,
    version: VersionOption = None,
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
