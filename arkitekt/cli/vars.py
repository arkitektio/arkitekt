import os

import typer
from rich.console import Console

from .errors import cli_error


def get_console(ctx: typer.Context) -> Console:
    try:
        return ctx.obj["console"]
    except LookupError:
        cli_error(
            "No Current Console. Probably you are not running this command from the CLI."
        )


def set_console(ctx: typer.Context, console: Console) -> None:
    ctx.obj["console"] = console


def get_work_dir(ctx: typer.Context) -> str:
    return ctx.obj.get("work_dir", os.getcwd())


def set_work_dir(ctx: typer.Context, work_dir: str) -> None:
    ctx.obj["work_dir"] = work_dir
