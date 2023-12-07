import rich_click as click
import subprocess
from .utils import search_username_in_docker_info
from arkitekt.cli.vars import get_console
from arkitekt.cli.types import Manifest
from rich.panel import Panel
from arkitekt.cli.io import get_builds, get_deployments, generate_deployment
from click import Context

def check_if_manifest_already_deployed(manifest: Manifest) -> None:
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
            deployment.manifest.identifier == manifest.identifier
            and deployment.manifest.version == manifest.version
        ):
            raise click.ClickException(
                f"Deployment of {manifest.identifier}/{manifest.version} already exists. You cannot deploy the same version twice."
            )

@click.command()
@click.option("--build", help="The build to use", type=str, default="latest")
@click.option("--tag", help="The tag to use")
@click.pass_context
def publish(ctx: Context, build: str , tag: str) -> None:
    """Deploys aa previous build to dockerhub"""

    console = get_console(ctx)

    builds = get_builds()
    assert (
        build in builds
    ), f"Build {build} not found. Please run `arkitekt build` first"
    build_model = builds[build]

    manifest = build_model.manifest
    if build_model.manifest.version == "dev":
        raise click.ClickException(
            "You cannot deploy a dev version. Please run `arkitekt version` first to set a version"
        )

    check_if_manifest_already_deployed(manifest)
    docker_info = subprocess.check_output(["docker", "info"]).decode("utf-8")
    username = search_username_in_docker_info(docker_info)
    if not username:
        username = click.prompt(
            "Could not find username in docker info. Please provide your docker username"
        )

    tag = tag or click.prompt(
        "The tag to use",
        default=f"{username}/{build_model.manifest.identifier}:{build_model.manifest.version}",
    )

    md = Panel("Building Docker Container")
    console.print(md)

    deployed = {}

    docker_run = subprocess.run(["docker", "tag", build_model.build_id, tag])
    if docker_run.returncode != 0:
        raise click.ClickException("Could not retag docker container")

    console.print(md)
    docker_run = subprocess.run(["docker", "push", tag])
    if docker_run.returncode != 0:
        raise click.ClickException("Could not push docker container")

    deployed["docker"] = tag

    generate_deployment(
        build_model,
        tag,
        with_definitions=False,
    )

    md = Panel(
        "[bold green] Sucessfully pushed your plugin to dockerhub. Make sure to commit and push your changes to github to make them available to others.",
        title="Yeah! Success",
        title_align="center",
        border_style="green",
        style="green",
    )
    console.print(md)
