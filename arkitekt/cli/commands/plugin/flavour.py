import typer

# `flavour add` reuses the plugin `init` scaffolder.
from .init import init

flavour = typer.Typer(
    no_args_is_help=True,
    help="""
    Manage the flavours the app is built into
    """,
)

# Register init as add
flavour.command("add")(init)
