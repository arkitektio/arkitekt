import typer

from arkitekt_next.cli.errors import cli_error
from arkitekt_next.cli.vars import get_work_dir, set_manifest
from arkitekt_next.cli.io import load_manifest
from arkitekt_next.utils import create_arkitekt_next_folder

from .init import init
from .build import build
from .validate import validate
from .publish import publish
from .stage import stage
from .flavour import flavour
from .selector import selector

plugin = typer.Typer(
    no_args_is_help=True,
    help="""Turn your app into a deployable Arkitekt plugin.

    A plugin is an app packaged (via a flavour Dockerfile) so it can be built and
    deployed onto any Arkitekt instance: initialize a flavour (`init`), build and
    publish the image (`build`, `publish`), validate flavours (`validate`), and
    manage flavours/selectors. These commands operate on the app in the current
    working directory and therefore require an already-initialized app — run
    `arkitekt-next app init` first.
    """,
)


@plugin.callback()
def plugin_callback(ctx: typer.Context) -> None:
    """Turn your app into a deployable Arkitekt plugin.

    A plugin is an app packaged (via a flavour Dockerfile) so it can be built and
    deployed onto any Arkitekt instance: initialize a flavour (`init`), build and
    publish the image (`build`, `publish`), validate flavours (`validate`), and
    manage flavours/selectors. These commands operate on the app in the current
    working directory and therefore require an already-initialized app — run
    `arkitekt-next app init` first.
    """
    # Guard: plugin commands only make sense inside an initialized app directory.
    # Top-level groups don't get the `app` group's manifest bootstrap, so load it
    # here (and fail clearly if this isn't an app) for the subcommands to use.
    work_dir = get_work_dir(ctx)
    manifest = load_manifest(base_dir=work_dir)
    if manifest is None:
        cli_error(
            f"No Arkitekt app found in '{work_dir}'. Plugin commands can only be run "
            "inside an initialized app directory — run `arkitekt-next app init` first."
        )

    create_arkitekt_next_folder(base_dir=work_dir)
    set_manifest(ctx, manifest)


plugin.command("init")(init)
plugin.command("build")(build)
plugin.command("validate")(validate)
plugin.command("publish")(publish)
plugin.command("stage")(stage)
plugin.add_typer(flavour, name="flavour")
plugin.add_typer(selector, name="selector")
