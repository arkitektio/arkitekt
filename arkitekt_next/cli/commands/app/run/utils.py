from importlib import import_module
from typing import Callable
from arkitekt_next.app.app import App

# Re-exported for backwards compatibility; the canonical definition now lives in
# `arkitekt_next.cli.options` alongside the shared option aliases.
from arkitekt_next.cli.options import LogLevel

__all__ = ["LogLevel", "import_builder", "run_app"]


def import_builder(builder: str) -> Callable[..., App]:
    """Import a builder function from a module.

    Parameters
    ----------
    builder : str
        The builder function to import, in the format "module.function".

    Returns
    -------
    Callable[..., App]
        The imported builder function.

    """

    module_path, function_name = builder.rsplit(".", 1)
    module = import_module(module_path)
    function = getattr(module, function_name)
    return function


async def run_app(app: App) -> None:
    """Run an app by entering its context and running the rekuest service.

    Parameters
    ----------
    app : App
        The app to run.

    """
    rekuest = app.services.get("rekuest")
    if not rekuest:
        raise Exception("No rekuest service found. We need this to run the app.")

    async with app:
        await rekuest.arun()
