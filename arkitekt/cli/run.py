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


async def run_costum(
    entrypoint,
    identifier,
    version,
    builder: str = "arkitekt.builders.easy",
    nocache=False,
):
    builder = import_builder(builder)

    import_entrypoint(entrypoint)

    app = builder(identifier, version, no_cache=nocache)

    panel = construct_run_panel(app)
    console.print(panel)

    async with app:
        await app.rekuest.run()


async def run_easy(manifest: Manifest, url, instance_id, headless=False, nocache=False):
    from arkitekt.builders import easy

    import_entrypoint(manifest.entrypoint)

    app = easy(
        manifest.identifier,
        version=manifest.version,
        logo=manifest.logo,
        url=url,
        instance_id=instance_id,
        headless=headless,
        no_cache=nocache,
    )

    panel = construct_run_panel(app)
    console.print(panel)

    async with app:
        await app.rekuest.run()


async def run_port(
    manifest: Manifest,
    url,
    token,
    instance_id,
    headless=True,
    nocache=False,
):
    from arkitekt.builders import port

    import_entrypoint(manifest.entrypoint)

    app = port(
        identifier=manifest.identifier,
        version=manifest.version,
        url=url,
        token=token,
        instance_id=instance_id,
        headless=headless,
        no_cache=nocache,
    )

    panel = construct_run_panel(
        app,
    )
    console.print(panel)

    async with app:
        await app.rekuest.run()
