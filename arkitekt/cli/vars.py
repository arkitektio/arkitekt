import contextvars
from rich.console import Console
import rich_click as click
from .types import Manifest


current_console: contextvars.ContextVar[Console] = contextvars.ContextVar(
    "current_console"
)
current_manifest: contextvars.ContextVar[Manifest] = contextvars.ContextVar(
    "current_manifest"
)


def get_console(ctx) -> Console:
    try:
        return ctx.obj["console"]
    except LookupError:
        raise click.ClickException(
            "No Current Console. Probably you are not running this command from the CLI."
        )


def set_console(ctx, console):
    ctx.obj["console"] = console


def get_manifest(ctx) -> Manifest:
    """Get the current manifest or raise an exception."""
    try:
        return ctx.obj["manifest"]
    except LookupError:
        raise click.ClickException(
            "No manifest found. You need to run the `arkitekt init` command first."
        )


def set_manifest(ctx, manifest):
    ctx.obj["manifest"] = manifest
