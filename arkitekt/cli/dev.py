from importlib import import_module, reload
import asyncio
from arkitekt import App
from watchfiles import awatch
from rich.panel import Panel
from watchfiles.filters import PythonFilter
import os
from rich import get_console
import sys
import inspect
from rekuest.definition.registry import get_default_definition_registry
from typing import MutableSet, Tuple, Any
from arkitekt.cli.ui import construct_changes_group, construct_app_group
from arkitekt.cli.utils import import_builder
from .types import Manifest


async def build_and_run(app: App):
    async with app:
        await app.rekuest.run()


class EntrypointFilter(PythonFilter):
    def __init__(self, entrypoint, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.entrypoint = entrypoint

    def __call__(self, change, path: str) -> bool:
        x = super().__call__(change, path)
        if not x:
            return False

        x = os.path.basename(path)
        module_name = x.split(".")[0]

        return module_name == self.entrypoint


class DeepFilter(PythonFilter):
    def __call__(self, change, path: str) -> bool:
        return super().__call__(change, path)


def reload_modules(reloadable_modules):
    for module in reloadable_modules:
        reload(sys.modules[module])


def check_deeps(changes: set):
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


def reset_structure():
    get_default_definition_registry().definitions.clear()


def is_entrypoint_change(
    changes: MutableSet[Tuple[Any, str]], entrypoint_real_path: str
) -> bool:
    for change, path in changes:
        if os.path.normpath(path) == entrypoint_real_path:
            return True
    return False


async def run_dev(
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
    entypoint_real_path = os.path.realpath(entrypoint_file)

    builder_func = import_builder(builder)

    console = get_console()

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
            try:
                raise future.exception()
            except Exception:
                console.print_exception()
                panel = Panel("Error running App", style="bold red", border_style="red")
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

        x = asyncio.create_task(build_and_run(app))
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
                if is_entrypoint_change(changes, entypoint_real_path):
                    panel = Panel(
                        "Detected Entrypoint change, resetting app",
                        style="bold cyan",
                        border_style="cyan",
                    )
                    console.print(panel)
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
            app: App = builder_func(
                identifier=identifier,
                version=version,
                logo=manifest.logo,
                **builder_kwargs,
            )
            group = construct_app_group(app)
            panel = Panel(group, style="bold green", border_style="green")
            console.print(panel)

            x = asyncio.create_task(build_and_run(app))
            x.add_done_callback(callback)
        except Exception:
            console.print_exception()
            panel = Panel(
                "Error building reloaded App", style="bold red", border_style="red"
            )
            console.print(panel)
