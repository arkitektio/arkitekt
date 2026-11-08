from typing import Annotated
import typer
from arkitekt.cli.completion import complete_flavours
from arkitekt.cli.errors import cli_error
import subprocess
from arkitekt.constants import DEFAULT_ARKITEKT_URL
from arkitekt.cli.options import UrlOption
from arkitekt.cli.ui import command_hint, escape, step
from arkitekt.cli.vars import get_console, get_work_dir


def stage(
    ctx: typer.Context,
    build: Annotated[
        str | None,
        typer.Option("--build", help="The build to use"),
    ] = None,
    flavour: Annotated[
        str | None,
        typer.Option(
            "--flavour",
            "-f",
            help="The flavour to stage. Default: the only one the build made",
            autocompletion=complete_flavours,
        ),
    ] = None,
    url: UrlOption = DEFAULT_ARKITEKT_URL,
) -> None:
    """Stage the latest build for testing

    Runs the image of the latest build (or of --build) as a temporary staged version
    of the app, against the local arkitekt instance, headlessly, on the app target
    the build recorded.
    """
    from .io import get_builds

    console = get_console(ctx)
    work_dir = get_work_dir(ctx)
    builds = list(get_builds(build, base_dir=work_dir).values())
    if not builds:
        cli_error(f"Could not find any builds. Build one first: `{command_hint('plugin build', work_dir)}`")

    if flavour is None:
        if len(builds) > 1:
            made = ", ".join(sorted(b.flavour for b in builds))
            cli_error(f"The build made several flavours ({made}): name one with --flavour.")
        build_model = builds[0]
    else:
        matching = [b for b in builds if b.flavour == flavour]
        if not matching:
            cli_error(
                f"Could not find a build for flavour {flavour}. Build it first: "
                f"`{command_hint(f'plugin build --flavour {flavour}', work_dir)}`"
            )
        build_model = matching[-1]

    command = build_model.build_docker_command() + build_model.build_arkitekt_command(url)

    step(
        console,
        f"Staging build {escape(build_model.build_id)} ({escape(build_model.flavour)})",
        f"against {escape(url)}",
    )
    console.print(f"  {escape(' '.join(command))}", highlight=False, soft_wrap=True)

    subprocess.run(" ".join(command), shell=True)

    cli_error("Docker container exited")
