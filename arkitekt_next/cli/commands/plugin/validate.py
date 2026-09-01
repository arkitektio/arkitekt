from typing import Annotated, Optional
import typer
from arkitekt_next.cli.vars import get_console, get_work_dir


def validate(
    ctx: typer.Context,
    flavour: Annotated[
        Optional[str],
        typer.Option("--flavour", "-f", help="Validate only this flavour."),
    ] = None,
) -> None:
    """Validates all Dockerfiles and flavour configs for this app."""
    from .io import get_flavours

    console = get_console(ctx)
    work_dir = get_work_dir(ctx)

    flavours = get_flavours(base_dir=work_dir, select=flavour)

    for name in flavours:
        console.print(f"[green]✓[/green] Flavour [bold]{name}[/bold] is valid")

    console.print("[green]All flavours are valid[/green]")
