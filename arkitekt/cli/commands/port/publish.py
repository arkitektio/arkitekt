import rich_click as click
import subprocess
from .utils import search_username_in_docker_info
from arkitekt.cli.vars import get_console
from arkitekt.cli.types import Build
from rich.panel import Panel
from arkitekt.cli.io import get_builds, get_deployments, generate_deployment
from click import Context
import uuid


def check_if_build_already_deployed(build: Build) -> None:
    """Checks if a manifest has already been deployed. If it has, it raises a click.ClickException.

    Parameters
    ----------
    manifest : Manifest
        THe manifest to check

    Raises
    ------
    click.ClickException
        A click exception if the manifest has already been deployed
    """
    config = get_deployments()
    for deployment in config.deployments:
        if (
            deployment.manifest.identifier == build.manifest.identifier
            and deployment.manifest.version == build.manifest.version
            and deployment.flavour == build.flavour
        ):
            raise click.ClickException(
                f"Deployment of {build.manifest.identifier}/{build.manifest.version} in the {build.flavour} flavour already exists."
                + " You cannot deploy a build twice for the same version and flavour"
            )


@click.command()
@click.option("--build", help="The build run to use", type=str, default=None)
@click.option("--tag", help="The tag to use")
@click.pass_context
def publish(ctx: Context, build: str, tag: str) -> None:
    """Deploys aa previous build to dockerhub"""

    console = get_console(ctx)

    deployment_run = str(uuid.uuid4())

    builds = get_builds(selected_run=build)

    if len(builds) == 0:
        raise click.ClickException("Could not find any builds")

    docker_info = subprocess.check_output(["docker", "info"]).decode("utf-8")
    username = search_username_in_docker_info(docker_info)
    if not username:
        username = click.prompt(
            "Could not find username in docker info. Please provide your docker username"
        )

    for build_id, build_model in builds.items():
        if build_model.manifest.version == "dev":
            raise click.ClickException(
                "You cannot deploy a dev version. Please run `arkitekt version` first to set a version"
            )

        check_if_build_already_deployed(build_model)

        tag = tag or click.prompt(
            "The tag to use",
            default=f"{username}/{build_model.manifest.identifier}:{build_model.manifest.version}-{build_model.flavour}",
        )

        md = Panel("Building Docker Container")
        console.print(md)

        docker_run = subprocess.run(["docker", "tag", build_model.build_id, tag])
        if docker_run.returncode != 0:
            raise click.ClickException("Could not retag docker container")

        console.print(md)
        docker_run = subprocess.run(["docker", "push", tag])
        if docker_run.returncode != 0:
            raise click.ClickException("Could not push docker container")

        generate_deployment(
            deployment_run,
            build_model,
            tag,
            definitions=[],
        )

        md = Panel(
            f"[bold green] Sucessfully pushed {tag} your plugin to dockerhub"
            + "We have also generated a deployment file for you. "
            + "Make sure to commit and push your changes to github to make them available to others.",
            title="Yeah! Success",
            title_align="center",
            border_style="green",
            style="green",
        )
        console.print(md)
