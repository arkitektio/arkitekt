import os
from contextvars import ContextVar
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


#: The --work-dir of the command running, for what is said deep in helpers that are
#: not handed the context (a hint that names a command depends on the project).
_work_dir: ContextVar[str | None] = ContextVar("arkitekt_cli_work_dir", default=None)


def get_work_dir(ctx) -> str:
    return ctx.obj.get("work_dir", os.getcwd())


def set_work_dir(ctx, work_dir: str):
    ctx.obj["work_dir"] = work_dir
    _work_dir.set(work_dir)


def current_work_dir() -> str:
    """The running command's --work-dir, or the current directory outside one."""
    return _work_dir.get() or os.getcwd()
