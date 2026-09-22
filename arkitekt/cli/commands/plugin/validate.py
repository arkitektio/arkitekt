from typing import Annotated, Optional
import typer
from arkitekt.cli.vars import get_console, get_work_dir


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

    for name, loaded in flavours.items():
        console.print(f"[green]✓[/green] Flavour [bold]{name}[/bold] is valid")

        # An image built for several architectures runs anywhere; a cpu selector
        # naming an arch pins its pods to one. Both are legal, together they
        # mean the deployer ignores half of what was built.
        pinned = [
            arch
            for selector in loaded.selectors
            for arch in [getattr(selector, "arch", None)]
            if selector.kind == "cpu" and isinstance(arch, str)
        ]
        if pinned and len(loaded.platforms) > 1:
            console.print(
                f"[yellow]  Flavour [bold]{name}[/bold] builds "
                f"{', '.join(loaded.platforms)} but its cpu selector pins arch "
                f"{', '.join(pinned)}. Drop the arch from the selector, or build only "
                "that platform.[/yellow]"
            )

    console.print("[green]All flavours are valid[/green]")
