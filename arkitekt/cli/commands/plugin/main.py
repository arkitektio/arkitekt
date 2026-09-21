import typer

from arkitekt.cli.vars import get_work_dir
from arkitekt.utils import create_arkitekt_folder

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
    `arkitekt init` first.
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
    `arkitekt init` first.
    """
    # Flavours, builds and deployments live in the `.arkitekt` folder. The app
    # itself is not loaded here: only the commands that need its identity (`init`
    # for a devcontainer, `build`) import it, from their own target, so that
    # `validate`, `publish` and `selector` never run the user's module.
    create_arkitekt_folder(base_dir=get_work_dir(ctx))


plugin.command("init")(init)
plugin.command("build")(build)
plugin.command("validate")(validate)
plugin.command("publish")(publish)
plugin.command("stage")(stage)
plugin.add_typer(flavour, name="flavour")
plugin.add_typer(selector, name="selector")
