import typer

from .inspect import inspect
from .scopes import scopes_group
from .version import version


manifest = typer.Typer(
    no_args_is_help=True,
    help="""Updates the manifest of this app

    The manifest is used to describe the app and its rights (scopes) and requirements, to be run on the platform.
    This manifest is used to authenticate the app with the platform establishing its scopes and requirements.



    """,
)


manifest.command("inspect")(inspect)
manifest.add_typer(scopes_group, name="scopes")
manifest.add_typer(version, name="version")
