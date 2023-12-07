import rich_click as click
from arkitekt.cli.vars import get_console, get_manifest
import os
from rich.panel import Panel
import subprocess
import uuid
from arkitekt.cli.io import generate_build
from click import Context

@click.command()
@click.option("--dockerfile", help="The dockerfile to use", default="Dockerfile")
@click.option(
    "--builder", help="The port builder to use", default="arkitekt.builders.port"
)
@click.pass_context
def build(ctx: Context, dockerfile: str, builder: str) -> None:
    """Builds the arkitekt app to docker"""

    build_id = str(uuid.uuid4())

    manifest = get_manifest(ctx)
    console = get_console(ctx)

    if not os.path.exists(dockerfile):
        raise click.ClickException(
            f"Dockerfile {dockerfile} does not exist. Please create a dockerfile first"
             "(e.g. with the port wizard command)."
        )

    md = Panel(
        "Building for Port", subtitle="This may take a while...", subtitle_align="right"
    )

    md = Panel("Building Docker Container")
    console.print(md)

    docker_run = subprocess.run(
        ["docker", "build", "-t", build_id, "-f", dockerfile or "Dockerfile", "."]
    )
    if docker_run.returncode != 0:
        raise click.ClickException("Could not build docker container")

    generate_build(builder, build_id, manifest)
