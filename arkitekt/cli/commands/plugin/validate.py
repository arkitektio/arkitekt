from typing import Annotated
import typer
from arkitekt.cli.completion import complete_flavours
from arkitekt.cli.ui import done, escape, notice
from arkitekt.cli.vars import get_console, get_work_dir


def validate(
    ctx: typer.Context,
    flavour: Annotated[
        str | None,
        typer.Option("--flavour", "-f", help="Validate only this flavour", autocompletion=complete_flavours),
    ] = None,
) -> None:
    """Validate every Dockerfile and flavour config of this app"""
    from .io import get_flavours

    console = get_console(ctx)
    work_dir = get_work_dir(ctx)

    flavours = get_flavours(base_dir=work_dir, select=flavour)

    for name, loaded in flavours.items():
        done(console, f"Flavour [bold]{escape(name)}[/bold] is valid")

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
            notice(
                console,
                f"Flavour [bold]{escape(name)}[/bold] builds {escape(', '.join(loaded.platforms))} "
                f"but its cpu selector pins arch {escape(', '.join(pinned))}",
                "drop the arch from the selector, or build only that platform",
            )

    done(console, "All flavours are valid")
