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
def remove(
    ctx: Context,
    name: Optional[str] = None,
) -> None:
    """
    Remove a deployment

    Removing a deployment will stop all containers and call docker compose down
    on the project. This will remove all containers and networks created by the
    deployment. As opposed to the down command, the deployment will also be
    removed from the .dokker folder, and all data stored in volumes managed by
    the deployment will be removed.

    This step is irreversible, so use with caution.

    """
    if not name:
        options = compile_options()
        if not options:
            raise click.ClickException(
                "No deployments found. Please run arkitekt server init first"
            )

        name = options[0]

    print(f"Running {name}")

    project = DokkerProject(
        name=name,
    )

    deployment = Deployment(project=project, logger=PrintLogger())

    with deployment:
        print("Shutting down...")
        deployment.down()

        print("Removing...")
        deployment.remove()

    print("Done")
