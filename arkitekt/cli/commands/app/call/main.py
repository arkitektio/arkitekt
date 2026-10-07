""" Calling functions in your arkitekt app"""

import typer


call = typer.Typer(
    no_args_is_help=True,
    help="""Call actions.

    `local` calls one of this app's own actions right here, with no server in
    between: the way to try an action while writing it. `remote` calls an action
    on the connected server, wherever it runs.
    """,
)

from .local import local
from .remote import remote

call.command("local")(local)
call.command("remote")(remote)
