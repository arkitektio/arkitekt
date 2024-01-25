from importlib import import_module, reload
import asyncio
from arkitekt import App
from watchfiles import awatch, Change
from rich.panel import Panel
from rich.console import Console
from watchfiles.filters import PythonFilter
import os
import sys
import inspect
from rekuest.definition.registry import get_default_definition_registry
from typing import MutableSet, Tuple, Any, Set
from arkitekt.cli.ui import construct_changes_group, construct_app_group
from arkitekt.cli.commands.run.utils import import_builder
from arkitekt.cli.types import Manifest
from arkitekt.apps.types import App
import rich_click as click
import os
from arkitekt.cli.options import (
    with_fakts_url,
    with_builder,
    with_token,
    with_instance_id,
    with_headless,
    with_log_level,
    with_skip_cache,
)
from arkitekt.cli.vars import get_console, get_manifest


class EntrypointFilter(PythonFilter):
    """Checks if the entrypoint is changed"""

    def __init__(self, entrypoint: str, *args, **kwargs) -> None:
        """A filter that checks if the entrypoint is changed

        Parameters
        ----------
        entrypoint : str
            The entrypoint to check
        """
        super().__init__(*args, **kwargs)
        self.entrypoint = entrypoint

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

        basename = os.path.basename(path)
        module_name = basename.split(".")[0]

        return module_name == self.entrypoint


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


async def run_app(app: App) -> None:
    """A helper function to run the app

    Parameters
    ----------
    app : App
        The app to run

    """
    async with app:
        await app.rekuest.run()


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
    get_default_definition_registry().definitions.clear()


def is_entrypoint_change(
    changes: MutableSet[Tuple[Any, str]], entrypoint_real_path: str
) -> bool:
    for change, path in changes:
        if os.path.normpath(path) == entrypoint_real_path:
            return True
    return False


async def run_dev(
    console: Console,
    manifest: Manifest,
    version=None,
    builder: str = "arkitekt.builders.easy",
    deep: bool = False,
    **builder_kwargs,
):
    entrypoint = manifest.entrypoint
    identifier = manifest.identifier
    version = version or "dev"
    entrypoint_file = f"{manifest.entrypoint}.py"
    os.path.realpath(entrypoint_file)

    builder_func = import_builder(builder)

    generation_message = "[not bold white]This is a development tool for arkitekt apps. It will watch your app for changes and reload it when it detects a change. It will also print out the current state of your app.[/]"

    if deep:
        generation_message += "\n\n - [not bold white][b]Deep mode[/] is enabled. This will watch all your installed packages for changes and reload them if they are changed.[/]"
    else:
        generation_message += "\n\n - [not bold white][b]Deep mode[/] is disabled. This will only watch your entrypoint for changes.[/]"

    panel = Panel(
        generation_message,
        style="bold green",
        border_style="green",
        title="Arkitekt Dev Mode",
    )
    console.print(panel)

    try:
        module = import_module(manifest.entrypoint)

    except Exception:
        console.print_exception()
        panel = Panel(
            f"Error while importing your entrypoint please fix your file {entrypoint} and save",
            style="bold red",
            border_style="red",
        )
        console.print(panel)
        module = None

    def callback(future):
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
                    panel = Panel(
                        "Error running App", style="bold red", border_style="red"
                    )
                    console.print(panel)

    try:
        app: App = builder_func(
            identifier=identifier,
            version=version,
            logo=manifest.logo,
            **builder_kwargs,
        )
        group = construct_app_group(app)
        panel = Panel(group, style="bold green", border_style="green")
        console.print(panel)

        x = asyncio.create_task(run_app(app))
        x.add_done_callback(callback)
    except Exception:
        console.print_exception()
        panel = Panel(
            "Error building initial App", style="bold red", border_style="red"
        )
        console.print(panel)

    async for changes in awatch(
        ".",
        watch_filter=EntrypointFilter(entrypoint) if not deep else DeepFilter(),
        debounce=2000,
        step=500,
    ):
        if deep:
            to_be_reloaded = check_deeps(changes)
            if not to_be_reloaded:
                continue

        group = construct_changes_group(changes)
        panel = Panel(group, style="bold blue", border_style="blue")
        console.print(panel)

        console.print(panel)
        # Cancelling the app
        if not x or x.done():
            pass

        else:
            x.cancel()
            panel = Panel(
                "Cancelling latest version", style="bold yellow", border_style="yellow"
            )
            console.print(panel)
            try:
                await x

            except asyncio.CancelledError:
                pass

        # Restarting the app
        try:
            with console.status("Reloading module..."):
                reset_structure()

                if not module:
                    module = import_module(entrypoint)
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
            app = builder_func(
                identifier=identifier,
                version=version,
                logo=manifest.logo,
                **builder_kwargs,
            )
            group = construct_app_group(app)
            panel = Panel(group, style="bold green", border_style="green")
            console.print(panel)

            x = asyncio.create_task(run_app(app))
            x.add_done_callback(callback)
        except Exception:
            console.print_exception()
            panel = Panel(
                "Error building reloaded App", style="bold red", border_style="red"
            )
            console.print(panel)


@click.command()
@with_fakts_url
@with_builder
@with_token
@with_instance_id
@with_headless
@with_log_level
@with_skip_cache
@click.option(
    "--deep",
    help="Should we check the whole directory for changes and reload them when changes?",
    is_flag=True,
)
@click.pass_context
def dev(ctx, **kwargs):
    """Runs the app in dev mode (with hot reloading)

    Running the app in dev mode will automatically reload the app when changes are detected.
    This is useful for development and debugging.
    """

    manifest = get_manifest(ctx)
    console = get_console(ctx)

    asyncio.run(run_dev(console, manifest, **kwargs))
