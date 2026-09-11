from rekuest import get_default_app_registry
from functools import partial
from importlib import import_module, reload
import asyncio

from watchfiles import awatch, Change
from rich.panel import Panel
from rich.console import Console
from watchfiles.filters import PythonFilter
import os
import sys
import inspect
from pathlib import Path
from rekuest.app import AppRegistry
from rekuest.agents.hooks.registry import get_default_hook_registry
from typing import Annotated, MutableSet, Optional, Tuple, Any, Set
import typer
from arkitekt.cli.ui import construct_changes_group, construct_app_group
from arkitekt.cli.commands.app.run.utils import import_builder, run_app
from arkitekt.cli.options import (
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
from arkitekt.cli.types import Manifest
from arkitekt.app.app import App
from arkitekt.constants import DEFAULT_ARKITEKT_URL
from arkitekt.cli.vars import get_console, get_manifest


class EntrypointFilter(PythonFilter):
    """Checks if the entrypoint is changed"""

    def __init__(self, entrypoint_real_path: str, *args, **kwargs) -> None:
        """A filter that checks if the entrypoint is changed

        Parameters
        ----------
        entrypoint_real_path : str
            The entrypoint to check
        """
        super().__init__(*args, **kwargs)
        self.entrypoint_real_path = os.path.normpath(entrypoint_real_path)

    def __call__(self, change: Change, path: str) -> bool:
        """Checks if any of the python filters are changed
        _description_
                Parameters
                ----------
                change : Change
                    The change type
                path : str
                    The causing path

                Returns
                -------
                bool
                    Should we reload?
        """
        x = super().__call__(change, path)
        if not x:
            return False

        return os.path.normpath(os.path.realpath(path)) == self.entrypoint_real_path


class DeepFilter(PythonFilter):
    """Checks if any of the python filters are changed"""

    def __call__(self, change: Change, path: str) -> bool:
        """Checks if any of the python filters are changed

        Parameters
        ----------
        change : Change
            The change type
        path : str
            The causing path

        Returns
        -------
        bool
            Should we reload?
        """
        return super().__call__(change, path)


def reload_modules(reloadable_modules) -> None:
    """Reloads the modules in the reloadable_modules set"""
    for module in reloadable_modules:
        reload(sys.modules[module])


def check_deeps(changes: Set[Tuple[Change, str]]) -> Set[str]:
    """Checks if any of the changes
    are happening in a module that is installed
    and returns the modules that should be reloaded



    Parameters
    ----------
    changes : Set[ Tuple[Change, str] ]
        The changes to check

    Returns
    -------
    Set[str]
        A set of modules that should be reloaded
    """
    normalized = [os.path.normpath(file) for modified, file in changes]

    reloadable_modules = set()

    for key, v in sys.modules.items():
        try:
            filepath = inspect.getfile(v)
        except OSError:
            continue
        except TypeError:
            continue

        for i in normalized:
            if filepath.startswith(i):
                reloadable_modules.add(key)

    return reloadable_modules


def reset_structure() -> None:
    """Resets the default defintiion rgistry and all
    regitered nodes"""
    get_default_app_registry().actor_builders.clear()
    get_default_hook_registry().reset()


def is_entrypoint_change(
    changes: MutableSet[Tuple[Any, str]], entrypoint_real_path: str
) -> bool:
    for change, path in changes:
        if os.path.normpath(path) == entrypoint_real_path:
            return True
    return False


def resolve_entrypoint(entrypoint: str) -> tuple[str, str]:
    """Returns the importable module path and watched file path."""
    cwd = Path.cwd()
    normalized_entrypoint = entrypoint.strip()
    has_path_separator = any(
        separator in normalized_entrypoint
        for separator in (os.sep, os.altsep)
        if separator
    )

    if normalized_entrypoint.endswith(".py") or has_path_separator:
        entrypoint_path = Path(normalized_entrypoint)
        if entrypoint_path.is_absolute():
            entrypoint_path = entrypoint_path.resolve().relative_to(cwd)

        if entrypoint_path.suffix == ".py":
            entrypoint_path = entrypoint_path.with_suffix("")

        module_path = ".".join(entrypoint_path.parts)
    else:
        module_path = normalized_entrypoint.strip(".")
        entrypoint_path = Path(*module_path.split("."))

    entrypoint_file = str((cwd / entrypoint_path).with_suffix(".py").resolve())

    return module_path, entrypoint_file


def callback(console: Console, future: asyncio.Task[None]):
    if future.cancelled():
        return
    else:
        has_exception = future.exception()

        if not has_exception:
            panel = Panel(
                "App finished running", style="bold yellow", border_style="yellow"
            )
            console.print(panel)
        else:
            try:
                raise has_exception
            except Exception:
                console.print_exception()
                panel = Panel("Error running App", style="bold red", border_style="red")
                console.print(panel)


async def run_dev(
    console: Console,
    manifest: Manifest,
    entrypoint: str | None = None,
    version: str | None = None,
    builder: str = "arkitekt.builders.easy",
    deep: bool = False,
    reauth: bool = False,
    **builder_kwargs,
):
    entrypoint = entrypoint or manifest.entrypoint
    version = version or "dev"

    entrypoint_module, entrypoint_file = resolve_entrypoint(entrypoint)

    builder_func = import_builder(builder)

    # Build the app from the manifest (identifier, logo, scopes, ...), overriding
    # the version with the dev sentinel (or an explicit --version). Shared between
    # the initial build and every hot reload so they can never diverge.
    # --reauth implies skipping the fakts cache; never clobber an explicit --no-cache.
    builder_args = {**manifest.to_builder_dict(), "version": version, **builder_kwargs}
    builder_args["no_cache"] = bool(builder_args.get("no_cache")) or reauth

    generation_message = "[not bold white]This is a development tool for arkitekt apps. It will watch your app for changes and reload it when it detects a change. It will also print out the current state of your app.[/]"

    if deep:
        generation_message += "\n\n - [not bold white][b]Deep mode[/] is enabled. This will watch all your installed packages for changes and reload them if they are changed.[/]"
    else:
        generation_message += "\n\n - [not bold white][b]Deep mode[/] is disabled. This will only watch your entrypoint for changes.[/]"

    panel = Panel(
        generation_message,
        style="bold green",
        border_style="green",
        title="ArkitektNext Dev Mode",
    )
    console.print(panel)

    try:
        module = import_module(entrypoint_module)

    except Exception:
        console.print_exception()
        panel = Panel(
            f"Error while importing your entrypoint please fix your file {entrypoint_file} and save",
            style="bold red",
            border_style="red",
        )
        console.print(panel)
        module = None

    current_run: asyncio.Future[None] | None = None
    # This is the main task that is running the app

    try:
        app: App = builder_func(**builder_args)
        group = construct_app_group(app)
        panel = Panel(group, style="bold green", border_style="green")
        console.print(panel)

        current_run = asyncio.create_task(run_app(app))
        current_run.add_done_callback(partial(callback, console))
    except Exception:
        console.print_exception()
        panel = Panel(
            "Error building initial App", style="bold red", border_style="red"
        )
        console.print(panel)

    async for changes in awatch(
        ".",
        watch_filter=EntrypointFilter(entrypoint_file) if not deep else DeepFilter(),
        debounce=2000,
        step=500,
    ):
        if deep:
            #
            to_be_reloaded = check_deeps(changes)
            if not to_be_reloaded:
                continue
        else:
            to_be_reloaded: Set[str] = set()

        group = construct_changes_group(changes)
        panel = Panel(group, style="bold blue", border_style="blue")
        console.print(panel)
        # Cancelling the app
        if not current_run or current_run.done():
            pass

        else:
            current_run.cancel()
            panel = Panel(
                "Cancelling latest version", style="bold yellow", border_style="yellow"
            )
            console.print(panel)
            try:
                await current_run

            except asyncio.CancelledError:
                pass

        # Restarting the app
        try:
            with console.status("Reloading module..."):
                reset_structure()

                if not module:
                    module = import_module(entrypoint_module)
                else:
                    if deep:
                        reload_modules(to_be_reloaded)
                    else:
                        reload(module)
        except Exception:
            console.print_exception()
            panel = Panel(
                "Reload unsucessfull please fix your app and save",
                style="bold red",
                border_style="red",
            )
            console.print(panel)
            continue

        try:
            app = builder_func(**builder_args)
            group = construct_app_group(app)
            panel = Panel(group, style="bold green", border_style="green")
            console.print(panel)

            current_run = asyncio.create_task(run_app(app))
            current_run.add_done_callback(partial(callback, console))
        except Exception:
            console.print_exception()
            panel = Panel(
                "Error building reloaded App", style="bold red", border_style="red"
            )
            console.print(panel)


def dev(
    ctx: typer.Context,
    entrypoint: Annotated[Optional[str], typer.Argument()] = None,
    url: UrlOption = DEFAULT_ARKITEKT_URL,
    builder: BuilderOption = "arkitekt.builders.easy",
    token: TokenOption = None,
    force: ForceOption = False,
    redeem_token: RedeemTokenOption = None,
    headless: HeadlessOption = False,
    log_level: LogLevelOption = LogLevel.ERROR,
    no_cache: NoCacheOption = False,
    version: VersionOption = None,
    deep: Annotated[
        bool,
        typer.Option(
            "--deep",
            help="Should we check the whole directory for changes and reload them when changes?",
        ),
    ] = False,
    reauth: Annotated[
        bool,
        typer.Option(
            "--reauth",
            help="Force a fresh login: skip the fakts cache and re-run authentication.",
        ),
    ] = False,
) -> None:
    """Runs the app in dev mode (with hot reloading)

    Running the app in dev mode will automatically reload the app when changes are detected.
    This is useful for development and debugging.
    """

    manifest = get_manifest(ctx)
    console = get_console(ctx)

    asyncio.run(
        run_dev(
            console,
            manifest,
            entrypoint=entrypoint,
            url=url,
            builder=builder,
            token=token,
            force=force,
            redeem_token=redeem_token,
            headless=headless,
            log_level=log_level.value,
            no_cache=no_cache,
            version=version,
            deep=deep,
            reauth=reauth,
        )
    )
