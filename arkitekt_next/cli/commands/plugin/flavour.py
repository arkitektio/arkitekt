import typer

# `flavour add` reuses the plugin `init` scaffolder.
from .init import init

flavour = typer.Typer(
    no_args_is_help=True,
    help="""
    Manage flavours
    """,
)

# Register init as add
flavour.command("add")(init)
