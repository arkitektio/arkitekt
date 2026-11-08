import typer

# `flavour add` is the scaffolder in init.py.
from .init import init

flavour = typer.Typer(
    no_args_is_help=True,
    help="""
    Manage the flavours the app is built into
    """,
)

# Register init as add
flavour.command("add")(init)
