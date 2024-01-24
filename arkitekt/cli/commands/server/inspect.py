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
import json

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
@click.pass_context
def inspect(
    ctx: Context,
    name: Optional[str] = None,
) -> None:
    """
    Inspect a deployment

    Inspect helps you find information about a deployment. It will show you
    information about the containers, networks and volumes created by the
    deployment. If you have not run arkitekt server init before, this will
    fail.

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

    with deployment:
        print(json.dumps(deployment.inspect().dict(), indent=4))
