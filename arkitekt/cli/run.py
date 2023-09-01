from importlib import import_module
from rich.console import Console
import asyncio
from .ui import construct_run_panel
from .utils import import_builder
from .types import Manifest

console = Console()


async def run_app(entrypoint, app):
    try:
        with console.status("Loading entrypoint module..."):
            try:
                import_module(entrypoint)
            except ModuleNotFoundError as e:
                console.print(f"Could not find entrypoint module {entrypoint}")
                raise e

        console.print("App is running...")
    except asyncio.CancelledError as e:
        console.print("Shutting down...")
        raise e


def import_entrypoint(entrypoint):
    with console.status("Loading entrypoint module..."):
        try:
            import_module(entrypoint)
        except ModuleNotFoundError as e:
            console.print(f"Could not find entrypoint module {entrypoint}")
            raise e


async def run_production(
    manifest: Manifest,
    entrypoint=None,
    builder: str = None,
    url=None,
    version=None,
    **builder_kwargs,
):
    builder = import_builder(builder)

    import_entrypoint(entrypoint or manifest.entrypoint)

    app = builder(
        identifier=manifest.identifier,
        version=version or manifest.version,
        logo=manifest.logo,
        url=url,
        **builder_kwargs,
    )

    panel = construct_run_panel(app)
    console.print(panel)

    async with app:
        await app.rekuest.run()
