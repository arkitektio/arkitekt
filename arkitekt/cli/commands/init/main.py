import rich_click as click
import os
from arkitekt.cli.constants import *
from getpass import getuser
from arkitekt.cli.types import Manifest, Requirement
from arkitekt.cli.vars import get_manifest, get_console
import semver
from arkitekt.cli.io import write_manifest
from rich.panel import Panel
from typing import Optional, List


def check_overwrite_app(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    app_file = ctx.params["entrypoint"] + ".py"
    if os.path.exists(app_file) and not value:
        should_overwrite = click.confirm(
            "Entrypoint File already exists. Do you want to overwrite?"
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
    "-om",
    help="Should we overwrite the existing manifest if it already exists?",
    is_flag=True,
    default=False,
    callback=check_overwrite,
)
@click.option(
    "--template",
    "-t",
    help="The template to use. You can choose from a variety of preconfigured templates. They are just starting points and can be changed later.",
    type=click.Choice(compile_templates()),
    default="simple",
)
@click.option(
    "--identifier",
    "-i",
    help="The identifier of your app. This will be used to identify your app in the Arkitekt ecosystem. It should be unique and should follow the [link=https://en.wikipedia.org/wiki/Reverse_domain_name_notation]reverse domain name notation[/link] (example: com.example.myapp)",
    prompt="Your app identifier",
    default=os.path.basename(os.getcwd()),
)
@click.option(
    "--version",
    "-v",
    help="The version of your app. Needs to follow [link=https://semver.org/]semantic versioning[/link].",
    default="0.0.1",
    callback=ensure_semver,
)
@click.option(
    "--author",
    help="The author of your app. This will be shown to users of your app",
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
    "--logo",
    help="Which logo to use for this app, needs to be a valid url",
    required=False,
)
@click.option(
    "--entrypoint",
    "-e",
    help="The entrypoint of your app. This will be the name of the python file. Omit the .py ending",
    prompt="Your app file",
    default="app",
)
@click.option(
    "--overwrite-app",
    "-oa",
    help="Do you want to overwrite the app file if it exists?",
    is_flag=True,
    default=False,
    callback=check_overwrite_app,
)
@click.option(
    "--requirements",
    "-r",
    help="Dedicated hardware requirements for this app. They will be used to inform Plugin Schedulers like port, on which compute resources to put your plugin app, once deployed.You can choose multiple for your app. For a list of requirements, run `arkitekt manifest requirements available`",
    type=click.Choice(compile_requirements()),
    multiple=True,
    default=[],
)
@click.option(
    "--scopes",
    "-s",
    help="The scopes of the app. You can choose multiple for your app. For a list of scopes, run `arkitekt manifest scopes available`",
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
    logo: Optional[str],
    scopes: List[str],
    template: str,
    requirements: List[Requirement],
    entrypoint: str,
    overwrite_manifest: bool,
    overwrite_app: bool,
):
    """Initializes an Arkitekt app

    This command will create a new Arkitekt app in the current directory. It will
    create a `.arkitekt` folder that will contain a manifest and a `app.py` file,
    which will serve as the entrypoint for your app. By default, the app will be
    initialized with a simple hello world app, but you can choose from a variety
    of templates.

    """

    console = get_console(ctx)

    manifest = Manifest(
        logo=logo,
        author=author,
        identifier=identifier,
        version=version,
        scopes=scopes,
        requirements=requirements,
        entrypoint=entrypoint,
    )

    with open(build_relative_dir("templates", f"{template}.py")) as f:
        template_app = f.read()

    if not os.path.exists(f"{entrypoint}.py") or overwrite_app:
        with open(f"{entrypoint}.py", "w") as f:
            f.write(template_app)

    write_manifest(manifest)
    md = Panel(
        f"{manifest.to_console_string()} was successfully initialized\n\n"
        + "[not bold white]We are excited to see what you come up with!",
        border_style="green",
        style="green",
    )
    console.print(md)
