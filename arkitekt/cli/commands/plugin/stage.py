from typing import Annotated, Optional
import typer
from arkitekt.cli.errors import cli_error
import subprocess
from arkitekt.constants import DEFAULT_ARKITEKT_URL


def stage(
    ctx: typer.Context,
    build: Annotated[
        Optional[str],
        typer.Option("--build", help="The build to use"),
    ] = None,
    flavour: Annotated[
        str,
        typer.Option("--flavour", "-f", help="The flavour to use"),
    ] = "vanilla",
    url: Annotated[
        str,
        typer.Option("--url", "-u", help="The fakts server to use"),
    ] = DEFAULT_ARKITEKT_URL,
) -> None:
    """Stages the latest Build for testing

    Stages the current build for testing. This will create a temporary staged version
    of the app that is run against the local arkitekt instance, headlessly, on the
    app target the build recorded.
    """
    from .io import get_builds

    builds = get_builds(build)

    if len(builds) == 0:
        cli_error("Could not find any builds")

    if len(builds) > 1:
        try:
            build_model = next(
                build for build in builds.values() if build.flavour == flavour
            )
        except StopIteration:
            cli_error(
                f"Could not find a build for flavour {flavour}. Please run `arkitekt port build` "
                + "first to build the flavour"
            )

    else:
        build_model = list(builds.values())[0]

    command = (
        build_model.build_docker_command()
        + build_model.build_arkitekt_command(url)
    )

    typer.echo(f"Staging build {build} with flavour {flavour} against {url}")
    typer.echo("Running command: " + " ".join(command))

    subprocess.run(" ".join(command), shell=True)

    cli_error("Docker container exited")
