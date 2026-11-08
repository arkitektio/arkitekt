import os
from rich.console import Console
from .errors import cli_error


def get_console(ctx) -> Console:
    try:
        return ctx.obj["console"]
    except LookupError:
        cli_error(
            "No Current Console. Probably you are not running this command from the CLI."
        )


def set_console(ctx, console):
    ctx.obj["console"] = console


def get_work_dir(ctx) -> str:
    return ctx.obj.get("work_dir", os.getcwd())


def set_work_dir(ctx, work_dir: str):
    ctx.obj["work_dir"] = work_dir
