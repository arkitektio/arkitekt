import typer

from .upgrade import upgrade
from .version import version
from .info import info

self_group = typer.Typer(
    no_args_is_help=True,
    help="""Manage the Arkitekt CLI / SDK installation itself.

    Meta commands that act on your local Arkitekt installation rather than on a
    specific app: upgrade the installed SDK packages (`upgrade`), print the
    installed version (`version`), or dump environment diagnostics (`info`).
    """,
)

self_group.command("upgrade")(upgrade)
self_group.command("version")(version)
self_group.command("info")(info)
