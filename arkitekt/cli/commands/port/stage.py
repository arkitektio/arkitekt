import rich_click as click
from arkitekt.cli.vars import get_manifest
from arkitekt.cli.types import Requirement
import subprocess
from click import Context
from arkitekt.cli.io import get_builds


@click.command()
@click.option("--build", help="The build to use", type=str, default="latest")
@click.option(
    "--url", help="The fakts server to use", type=str, default="localhost:8000"
)
@click.option(
    "--builder", help="The builder to use", type=str, default="arkitekt.builders.easy"
)
@click.pass_context
def stage(ctx: Context, build: str, url: str, builder: str) -> None:
    """Stages the latest Build for testing

    Stages the current build for testing. This will create a temporary staged version
    of the app that is run agains the local arkitekt instance. The builder will be changed
    to the easy or provided builder to ensure that the app can be run headlessly


    """

    manifest = get_manifest(ctx)

    builds = get_builds()
    assert (
        build in builds
    ), f"Build {build} not found. Please run `arkitekt build` first"
    build_model = builds[build]
    build_id = build_model.build_id

    base_command = ["docker", "run", "-it"]
    with_network = ["--net", "host"]
    with_gpus = ["--gpus", "all"]
    with_build_id = [build_id]
    with_builder = ["arkitekt", "run", "prod", "--builder", builder, "--headless"]
    with_url = ["--url", url]

    # Bulding the command
    command = base_command
    command += with_network

    if Requirement.GPU.value in manifest.requirements:
        click.echo("GPU Requirement found. Staging with GPU")
        command += with_gpus

    command += with_build_id
    command += with_builder
    command += with_url

    click.echo(f"Running inside docker: {manifest.identifier}:{manifest.version}")
    docker_run = subprocess.run(command)

    message_string = (
        docker_run.stdout.decode("utf-8")
        if docker_run.stdout
        else "" + docker_run.stderr.decode("utf-8")
        if docker_run.stderr
        else ""
    )

    if "No manifest found" in message_string:
        raise click.ClickException(
            "Looks like the docker container could not find the manifest. Did you mount the '.arkitekt folder' correctly?"
        )

    raise click.ClickException("Docker container exited")
