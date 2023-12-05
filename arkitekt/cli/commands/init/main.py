import rich_click as click
import os
from arkitekt.cli.constants import *
from getpass import getuser
from arkitekt.cli.types import Manifest
from arkitekt.cli.vars import get_manifest, get_console
import semver
from arkitekt.cli.io import write_manifest
from rich.panel import Panel


def check_overwrite_app(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    app_file = ctx.params["app"] + ".py"
    if os.path.exists(app_file) and not value:
        should_overwrite = click.confirm(
            f"App File already exists. Do you want to overwrite?"
        )
        return should_overwrite

    return value


def check_overwrite(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    try:
        manifest = get_manifest(ctx)
        if not value:
            should_overwrite = click.confirm(
                f"Another Arkitekt app {manifest.to_console_string()} exists already at {os.getcwd()}?. Do you want to overwrite?",
                abort=True,
            )
            if not should_overwrite:
                ctx.abort()
    except click.ClickException:
        pass

    return value


def ensure_semver(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    if not value:
        value = click.prompt(
            "The version of your app",
            default="0.0.1",
        )

    while not semver.Version.is_valid(value):
        get_console().print(
            "Arkitekt versions need to follow [link=https://semver.org]semver[/link]. Please choose a correct format (examples: 0.0.0, 0.1.0, 0.0.0-alpha.1)"
        )
        value = click.prompt(
            "The version of your app",
            default="0.0.1",
        )

    return value


@click.command()
@click.option(
    "--overwrite-manifest",
    help="Should we overwrite the existing manifest?",
    is_flag=True,
    default=False,
    callback=check_overwrite,
)
@click.option(
    "--template",
    help="The template to use",
    type=click.Choice(compile_templates()),
    default="simple",
)
@click.option(
    "--identifier",
    help="The identifier of your app",
    prompt="Your app name",
    default=os.path.basename(os.getcwd()),
)
@click.option(
    "--version", help="The version of your app", default="0.0.1", callback=ensure_semver
)
@click.option(
    "--author",
    help="The author of your app",
    prompt="Your name",
    default=getuser(),
)
@click.option(
    "--template",
    help="Which template to use top create entrypoint",
    prompt="Your app file template",
    type=click.Choice(compile_templates()),
    default="simple",
)
@click.option(
    "--app",
    help="The entrypoint of your app. This will be the name of the python file",
    prompt="Your app file",
    default="app",
)
@click.option(
    "--overwrite-app",
    help="The entrypoint of your app. This will be the name of the python file",
    is_flag=True,
    default=False,
    callback=check_overwrite_app,
)
@click.option(
    "--requirements",
    "-r",
    help="Hardware requirements of this app",
    type=click.Choice(compile_requirements()),
    multiple=True,
    default=[],
)
@click.option(
    "--scopes",
    "-s",
    help="The scope of the app",
    type=click.Choice(compile_scopes()),
    multiple=True,
    default=["read"],
)
@click.pass_context
def init(
    ctx,
    identifier: str,
    version: str,
    author: str,
    scopes: List[str],
    template: str,
    requirements: List[str],
    app: str,
    overwrite_manifest: bool,
    overwrite_app: bool,
):
    """Initializes the arkitekt app"""

    print(identifier, version, author)
    console = get_console(ctx)

    manifest = Manifest(
        author=author,
        identifier=identifier,
        version=version,
        scopes=scopes,
        requirements=requirements,
        entrypoint=app,
    )

    with open(build_relative_dir("templates", f"{template}.py")) as f:
        template_app = f.read()

    if not os.path.exists("app") or overwrite_app:
        with open(f"{app}.py", "w") as f:
            f.write(template_app)

    write_manifest(manifest)
    md = Panel(
        f"{manifest.to_console_string()} was successfully initialized\n\n"
        + "[not bold white]We are excited to see what you come up with!",
        border_style="green",
        style="green",
    )
    console.print(md)
