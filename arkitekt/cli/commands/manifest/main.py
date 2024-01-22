import rich_click as click
from .inspect import inspect
from .scopes import scopes_group
from .version import version
from .wizard import wizard


@click.group()
@click.pass_context
def manifest(ctx) -> None:
    """Updates the manifest of this app

    The manifest is used to describe the app and its rights (scopes) and requirements, to be run on the platform.
    This manifest is used to authenticate the app with the platform establishing its scopes and requirements.



    """
    pass


manifest.add_command(inspect, "inspect")
manifest.add_command(scopes_group, "scopes")
manifest.add_command(version, "version")
manifest.add_command(wizard, "wizard")
