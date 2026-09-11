""" Calling functions in your arkitekt app"""

import typer


call = typer.Typer(
    no_args_is_help=True,
    help="""Call functions in your arkitekt app.

    Calls always go through a rekuest server: the function is assigned and run
    remotely using rekuest/fakts. Only nodes that are available on the connected
    server can be called.
    """,
)

from .remote import remote

call.command("remote")(remote)
