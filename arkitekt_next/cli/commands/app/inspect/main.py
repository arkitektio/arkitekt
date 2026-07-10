import typer

inspect = typer.Typer(
    no_args_is_help=True,
    help="""Inspects your arkitekt_next app

    Inspects various parts of your arkitekt_next app. This is useful for debugging
    and development. It also represents methods that are called by the arkitekt_next
    server when you run your app in production mode.

    """,
)

from .variables import variables
from .implementations import implementations
from .requirements import requirements
from .all import all

inspect.command("all")(all)
inspect.command("variables")(variables)
inspect.command("requirements")(requirements)
inspect.command("implementations")(implementations)
