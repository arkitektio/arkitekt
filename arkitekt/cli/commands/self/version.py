"""The ``arkitekt self version`` command.

Shows the installed version of the Arkitekt CLI and, optionally, every installed
package of the Arkitekt ecosystem.
"""

import platform
import sys
from importlib.metadata import version as installed_version, PackageNotFoundError
from typing import Annotated

import typer
from rich.table import Table

from arkitekt.cli.vars import get_console
from .constants import ARKITEKT_PACKAGES


def version(
    ctx: typer.Context,
    show_all: Annotated[
        bool,
        typer.Option(
            "--all",
            "-a",
            help="Show the version of every installed Arkitekt ecosystem package.",
        ),
    ] = False,
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            help="Print just the arkitekt version string (useful for scripts).",
        ),
    ] = False,
) -> None:
    """Show the installed Arkitekt CLI version.

    Prints the installed `arkitekt` version (and the Python it runs on). Use
    `--all` to list every installed Arkitekt ecosystem package, or `--plain` to
    emit just the version string for scripting.
    """
    console = get_console(ctx)

    try:
        own = installed_version("arkitekt")
    except PackageNotFoundError:
        own = "unknown"

    if plain:
        # Bypass rich formatting so the output is a clean, parseable string.
        typer.echo(own)
        return

    console.print(f"[bold]arkitekt[/bold] [green]{own}[/green]")
    console.print(
        f"[dim]Python {platform.python_version()} ({sys.implementation.name}) on {platform.system()}[/dim]"
    )

    if not show_all:
        return

    table = Table(title="Arkitekt ecosystem")
    table.add_column("Package", style="bold")
    table.add_column("Version", style="green")
    for name in ARKITEKT_PACKAGES:
        try:
            table.add_row(name, installed_version(name))
        except PackageNotFoundError:
            table.add_row(name, "[dim]not installed[/dim]")
    console.print(table)
