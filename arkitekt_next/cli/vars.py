import contextvars
import os
from rich.console import Console
from .errors import cli_error
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
        cli_error(
            "No Current Console. Probably you are not running this command from the CLI."
        )


def set_console(ctx, console):
    ctx.obj["console"] = console


def get_manifest(ctx) -> Manifest:
    """Get the current manifest or raise an exception."""
    try:
        return ctx.obj["manifest"]
    except LookupError:
        cli_error(
            "No manifest found. You need to run the `arkitekt_next init` command first."
        )


def set_manifest(ctx, manifest):
    ctx.obj["manifest"] = manifest


def get_work_dir(ctx) -> str:
    return ctx.obj.get("work_dir", os.getcwd())


def set_work_dir(ctx, work_dir: str):
    ctx.obj["work_dir"] = work_dir
