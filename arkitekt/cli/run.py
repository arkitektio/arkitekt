from importlib import import_module
from rich.console import Console
import asyncio
from .ui import construct_run_panel
from .utils import import_builder

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
    entrypoint, identifier, version, builder: str = "arkitekt.builders.easy"
):
    builder = import_builder(builder)

    import_entrypoint(entrypoint)

    app = builder(identifier, version)

    panel = construct_run_panel(app)
    console.print(panel)

    async with app:
        await app.rekuest.run()


async def run_easy(entrypoint, identifier, version, url, instance_id):
    from arkitekt.builders import easy

    import_entrypoint(entrypoint)

    app = easy(identifier, version, url=url, instance_id=instance_id)

    panel = construct_run_panel(app)
    console.print(panel)

    async with app:
        await app.rekuest.run()


async def run_port(entrypoint, identifier, version, url, token, instance_id):
    from arkitekt.builders import port

    import_entrypoint(entrypoint)

    app = port(identifier, version, url=url, token=token,  instance_id=instance_id)

    panel = construct_run_panel(
        app,
    )
    console.print(panel)

    async with app:
        await app.rekuest.run()
