import typer

inspect = typer.Typer(
    no_args_is_help=True,
    help="""Inspects your arkitekt app

    Inspects various parts of your arkitekt app. This is useful for debugging
    and development. It also represents methods that are called by the arkitekt
    server when you run your app in production mode.

    """,
)

from .variables import variables
from .implementations import implementations
from .requirements import requirements
from .services import services
from .hooks import hooks
from .lifecycle import lifecycle
from .all import all

inspect.command("all")(all)
inspect.command("variables")(variables)
inspect.command("requirements")(requirements)
inspect.command("implementations")(implementations)
inspect.command("services")(services)
inspect.command("hooks")(hooks)
inspect.command("lifecycle")(lifecycle)
