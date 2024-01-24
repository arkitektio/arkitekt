import rich_click as click
from click import Context
from dokker.projects.dokker import DokkerProject
from dokker.loggers.print import PrintLogger
from dokker.deployment import Deployment
from typing import Optional
import os
from .utils import compile_options
from rich.table import Table
from rich.live import Live
from arkitekt.cli.vars import get_console
import webbrowser

DEFAULT_REPO_URL = (
    "https://raw.githubusercontent.com/jhnnsrs/konstruktor/master/repo/channels.json"
)


@click.command()
@click.option(
    "--name",
    help="The name of the deployment",
    default=None,
    required=False,
    type=click.Choice(compile_options()),
)
@click.argument("services", nargs=-1, required=False)
@click.pass_context
def open(
    ctx: Context,
    name: Optional[str] = None,
    services: list[str] = None,
) -> None:
    """
    Opens a service in the browser

    This will open the service in the browser. If you have not run arkitekt server init
    before, this will fail.


    """
    if not name:
        options = compile_options()
        if not options:
            raise click.ClickException(
                "No deployments found. Please run arkitekt server init first"
            )

        name = options[0]

    project = DokkerProject(
        name=name,
    )

    console = get_console(ctx)

    deployment = Deployment(project=project)

    if not services:
        services = ["orkestrator"]

    with deployment:
        for service in services:
            link = deployment.inspect().find_service(service).get_label("arkitekt.link")
            console.print(f"Opening {service} at [link={link}]{link}[/link]")
            webbrowser.open(link)
