from typing import Annotated, List

import typer
from rich.table import Table
from rich.panel import Panel
from rich.console import Group
from arkitekt_next.cli.vars import get_console, get_manifest, get_work_dir
from arkitekt_next.cli.constants import compile_scopes
from arkitekt_next.cli.io import write_manifest
from arkitekt_next.cli.errors import cli_error


scopes_group = typer.Typer(
    no_args_is_help=True,
    help="""Inspect, add and remove scopes for this arkitekt-next app.""",
)


def _validate_scopes(value: List[str]) -> List[str]:
    available = compile_scopes()
    for scope in value or []:
        if scope not in available:
            raise typer.BadParameter(
                f"{scope!r} is not one of {list(available)}."
            )
    return value


def add_scopes(
    ctx: typer.Context,
    scope: Annotated[List[str], typer.Argument(callback=_validate_scopes)] = None,
) -> None:
    """Add one or more scopes to this app."""
    if not scope:
        cli_error("Please provide at least one scope")

    manifest = get_manifest(ctx)
    console = get_console(ctx)
    manifest.scopes = list(set(list(scope) + list(manifest.scopes)))
    write_manifest(manifest, base_dir=get_work_dir(ctx))
    console.print(f"Scopes updated to {manifest.scopes}")


def remove_scopes(
    ctx: typer.Context,
    scope: Annotated[List[str], typer.Argument(callback=_validate_scopes)] = None,
) -> None:
    """Remove one or more scopes from this app."""
    if not scope:
        cli_error("Please provide at least one scope to remove")

    manifest = get_manifest(ctx)
    console = get_console(ctx)
    manifest.scopes = list(set(manifest.scopes) - set(scope))
    write_manifest(manifest, base_dir=get_work_dir(ctx))
    console.print(f"Scopes updated to {manifest.scopes}")


def list_scopes(ctx: typer.Context) -> None:
    """List currently active scopes for this app."""
    manifest = get_manifest(ctx)
    console = get_console(ctx)

    table = Table.grid(padding=(0, 1))
    table.add_column("Scope")
    table.add_column("Description")
    for scope in manifest.scopes:
        table.add_row(scope, "")

    console.print(Panel(
        Group("[bold green]Demanded Scopes[/]", table),
        title_align="center",
        border_style="green",
        style="white",
    ))


def list_available(ctx: typer.Context) -> None:
    """List all scopes available in the platform."""
    console = get_console(ctx)

    table = Table.grid(padding=(0, 1))
    table.add_column("Scope")
    table.add_column("Description")
    for scope in compile_scopes():
        table.add_row(scope, "")

    console.print(Panel(
        Group("[bold green]Available Scopes[/]", table),
        title_align="center",
        border_style="green",
        style="white",
    ))


scopes_group.command("add")(add_scopes)
scopes_group.command("remove")(remove_scopes)
scopes_group.command("list")(list_scopes)
scopes_group.command("available")(list_available)
