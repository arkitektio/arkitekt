import rich_click as click
from click import Context
from dokker.projects.dokker import DokkerProject
from dokker.loggers.print import PrintLogger
from dokker.deployment import Deployment
from typing import Optional
import os
from .utils import compile_options


@click.command()
@click.option(
    "--name",
    help="The name of the deployment",
    default=None,
    required=False,
    type=click.Choice(compile_options()),
)
@click.pass_context
def stop(
    ctx: Context,
    name: Optional[str] = None,
) -> None:
    """
    Stop a deployment

    Stopping a deployment will stop all containers and call docker compose stop
    on the project. This will stop all containers and networks created by the
    deployment. The deployment will still be available in the .dokker folder

    This should not be confused with the down command, which will remove all
    containers and remove all networks created by the deployment.

    """
    if not name:
        options = compile_options()
        if not options:
            raise click.ClickException(
                "No deployments found. Please run arkitekt server init first"
            )

        name = options[0]

    print(f"Stopping {name}")

    project = DokkerProject(
        name=name,
    )

    deployment = Deployment(project=project, logger=PrintLogger())

    with deployment:
        print("Shutting down...")
        deployment.stop()

    print("Done")
