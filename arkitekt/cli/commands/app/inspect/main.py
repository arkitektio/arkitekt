import typer

inspect = typer.Typer(
    no_args_is_help=True,
    help="""Inspect what the app declares, without running it

    Inspects various parts of your arkitekt app. This is useful for debugging
    and development. It also represents methods that are called by the arkitekt
    server when you run your app in production mode.

    """,
)

from .all import all
from .clients import clients
from .implementations import implementations
from .lifecycle import lifecycle
from .requirements import requirements
from .structures import structures
from .variables import variables

inspect.command("all")(all)
inspect.command("variables")(variables)
inspect.command("requirements")(requirements)
inspect.command("implementations")(implementations)
inspect.command("clients")(clients)
inspect.command("structures")(structures)
inspect.command("lifecycle")(lifecycle)
