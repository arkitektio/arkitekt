import rich_click as click
from click import Context
from dokker.projects.contrib.konstruktor import KonstruktorProject
from dokker.projects.local import LocalProject
from dokker.loggers.print import PrintLogger
from dokker.deployment import Deployment
import asyncio
from typing import Optional, Any
import os
from .utils import compile_options

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
def up(
    ctx: Context,
    name: Optional[str] = None,
) -> None:
    """
    Initializes a new deployment from a konstruktor template.
    this will create a new folder in the .arkitekt/deployments folder
    with the name of the deployment and the docker-compose.yml file

    """
    if not name:
        options = compile_options()
        if not options:
            raise click.ClickException(
                "No deployments found. Please run arkitekt server init first"
            )

        name = options[0]

    print(f"Running {name}")

    project = LocalProject(
        compose_files=[
            os.path.join(
                os.getcwd(), ".arkitekt", "deployments", name, "docker-compose.yaml"
            )
        ],
    )

    deployment = Deployment(project=project, logger=PrintLogger())
    deployment.up_on_enter = True

    with deployment:
        input("Press Enter to stop the deployment")
