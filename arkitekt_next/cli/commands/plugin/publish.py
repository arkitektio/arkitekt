from typing import Annotated, Optional
import typer
import subprocess
from arkitekt_next.cli.errors import cli_error
from arkitekt_next.cli.interactive import require_interactive
from arkitekt_next.cli.vars import get_console
from rich.panel import Panel
import uuid


def check_if_build_already_deployed(build: "Build") -> None:
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
    from .io import get_deployments

    config = get_deployments()
    for deployment in config.app_images:
        if (
            deployment.manifest.identifier == build.manifest.identifier
            and deployment.manifest.version == build.manifest.version
            and deployment.flavour_name == build.flavour
        ):
            cli_error(
                f"Deployment of {build.manifest.identifier}/{build.manifest.version} in the {build.flavour} flavour already exists."
                + " You cannot deploy a build twice for the same version and flavour"
            )


def publish(
    ctx: typer.Context,
    build: Annotated[
        Optional[str],
        typer.Option("--build", help="The build run to use"),
    ] = None,
    tag: Annotated[
        Optional[str],
        typer.Option("--tag", help="The tag to use"),
    ] = None,
) -> None:
    """Deploys aa previous build to dockerhub"""
    from .utils import search_username_in_docker_info
    from .io import get_builds, generate_deployment

    console = get_console(ctx)

    deployment_run = str(uuid.uuid4())

    builds = get_builds(selected_run=build)

    if len(builds) == 0:
        cli_error("Could not find any builds")

    docker_info = subprocess.check_output(["docker", "info"]).decode("utf-8")
    username = search_username_in_docker_info(docker_info)
    if not username:
        require_interactive(
            "Providing a docker username",
            hint="Log in to docker (so `docker info` reports a username) to run non-interactively.",
        )
        username = typer.prompt(
            "Could not find username in docker info. Please provide your docker username"
        )

    for build_id, build_model in builds.items():
        if build_model.manifest.version == "dev":
            cli_error(
                "You cannot deploy a dev version. Please run `arkitekt_next version` first to set a version"
            )

        check_if_build_already_deployed(build_model)

        if not tag:
            require_interactive(
                "Choosing a docker tag",
                hint="Pass --tag to set the tag non-interactively.",
            )
            tag = typer.prompt(
                "The tag to use",
                default=f"{username}/{build_model.manifest.identifier}:{build_model.manifest.version}-{build_model.flavour}",
            )

        md = Panel("Building Docker Container")
        console.print(md)

        docker_run = subprocess.run(["docker", "tag", build_model.build_id, tag])
        if docker_run.returncode != 0:
            cli_error("Could not retag docker container")

        console.print(md)
        docker_run = subprocess.run(["docker", "push", tag])
        if docker_run.returncode != 0:
            cli_error("Could not push docker container")

        generate_deployment(
            deployment_run,
            build_model,
            tag,
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
