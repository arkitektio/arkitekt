import typer

run = typer.Typer(
    no_args_is_help=True,
    help="""Runs your arkitekt app

    Running your app locally is the first step to developing your app. You can run your app in
    development mode, which will automatically reload your app when you change the code, or in
    production mode, which does not reload your app when you change the code.



    """,
)

from .dev import dev
from .prod import prod

run.command("dev")(dev)
run.command("prod")(prod)
