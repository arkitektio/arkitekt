"""The ``arkitekt-next self info`` command.

A small "doctor"-style helper that prints the environment the CLI is running in:
Python, package manager, Docker availability and the install location of the
Arkitekt CLI. Useful when filing a bug report or debugging a broken setup.
"""

import platform
import shutil
import sys
from importlib.metadata import version as installed_version, PackageNotFoundError

import typer
from rich.table import Table

from arkitekt_next.cli.vars import get_console, get_work_dir


def _which_version(executable: str, args: list[str]) -> str:
    """Return ``<path> (<--version output>)`` for a tool, or ``not installed``."""
    path = shutil.which(executable)
    if not path:
        return "[yellow]not installed[/yellow]"
    import subprocess

    try:
        out = subprocess.run(
            [executable, *args], capture_output=True, text=True, timeout=5
        )
        line = (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr) else ""
        return f"{path}{f' ([green]{line}[/green])' if line else ''}"
    except Exception:
        return path


def info(ctx: typer.Context) -> None:
    """Print environment diagnostics for the Arkitekt CLI.

    Shows the installed CLI version, the Python interpreter, the available
    package managers (`uv`/`pip`), whether Docker is reachable, and the current
    working directory — a quick health check to paste into a bug report.
    """
    console = get_console(ctx)

    try:
        own = installed_version("arkitekt-next")
    except PackageNotFoundError:
        own = "unknown"

    table = Table(title="arkitekt-next environment", show_header=False)
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value")

    table.add_row("arkitekt-next", f"[green]{own}[/green]")
    table.add_row("Python", f"{platform.python_version()} ({sys.implementation.name})")
    table.add_row("Interpreter", sys.executable)
    table.add_row("Platform", f"{platform.system()} {platform.release()} ({platform.machine()})")
    table.add_row("uv", _which_version("uv", ["--version"]))
    table.add_row("pip", _which_version("pip", ["--version"]))
    # Docker is optional — only the `hub`/`coord`/`hubinator` up commands need it.
    table.add_row("docker [dim](optional)[/dim]", _which_version("docker", ["--version"]))
    table.add_row("Working dir", get_work_dir(ctx))

    console.print(table)
