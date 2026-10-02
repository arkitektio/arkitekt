from typing import TYPE_CHECKING, Annotated, Optional
import typer
import subprocess
from arkitekt.cli.errors import cli_error
from arkitekt.cli.tty import require_tty
from arkitekt.cli.vars import get_console, get_work_dir
from arkitekt.cli.ui import done, escape, notice, step
import uuid

if TYPE_CHECKING:
    from .types import Build


def check_if_build_already_deployed(build: "Build", work_dir: Optional[str] = None) -> None:
    """Checks if a build has already been deployed; aborts via cli_error if so."""
    from .io import get_deployments

    config = get_deployments(base_dir=work_dir)
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


def push_multi_arch(build_model: "Build", tag: str, work_dir: str, console) -> None:
    """Push every platform of a build as one manifest list.

    A multi-platform image only exists in a registry, so it cannot be assembled
    from the single image ``plugin build`` loaded locally: buildx builds and
    pushes in one step. The layers come straight out of the builder cache that
    build filled, so this is a near-no-op rebuild rather than a second build —
    but it *is* a build of the current sources, so publish from the tree that
    was built.
    """
    from .build import flavour_relative_dir
    from .buildx import ensure_builder
    from .io import get_flavours

    flavour = get_flavours(base_dir=work_dir, select=build_model.flavour).get(
        build_model.flavour
    )
    if flavour is None:
        cli_error(
            f"Build {build_model.build_id} was made from flavour '{build_model.flavour}', "
            "which no longer exists. Re-run `arkitekt plugin build`."
        )

    builder = ensure_builder(build_model.platforms, console=console)
    command = flavour.generate_build_command(
        tag,
        flavour_relative_dir(build_model.flavour),
        platform=",".join(build_model.platforms),
        output="--push",
        builder=builder,
    )

    console.print(
        f"Pushing {', '.join(build_model.platforms)} as one image, from the build cache."
    )
    docker_run = subprocess.run(command, cwd=work_dir)
    if docker_run.returncode != 0:
        cli_error(f"Could not push the multi-platform image (`{' '.join(command)}` failed)")


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
    """Deploy a previous build to Docker Hub."""
    from .utils import search_username_in_docker_info
    from .io import get_builds, generate_deployment

    console = get_console(ctx)
    work_dir = get_work_dir(ctx)

    deployment_run = str(uuid.uuid4())

    builds = get_builds(selected_run=build, base_dir=work_dir)

    if len(builds) == 0:
        cli_error("Could not find any builds")

    docker_info = subprocess.check_output(["docker", "info"]).decode("utf-8")
    username = search_username_in_docker_info(docker_info)
    if not username:
        require_tty(
            "Providing a docker username",
            hint="Log in to docker (so `docker info` reports a username) to run non-interactively.",
        )
        username = typer.prompt(
            "Could not find username in docker info. Please provide your docker username"
        )

    for build_id, build_model in builds.items():
        if build_model.manifest.version == "dev":
            cli_error(
                "You cannot deploy a dev version. Please run `arkitekt version` first to set a version"
            )

        check_if_build_already_deployed(build_model, work_dir)

        if build_model.inspection is None:
            # The deployment record requires an inspection, and the push happens
            # first: without this the image lands in the registry and *then* the
            # command dies writing deployments.yaml.
            cli_error(
                f"Build {build_model.build_id} was made with --no-inspect, and a deployment "
                "records what the image offers. Re-run `arkitekt plugin build` without it."
            )

        if not tag:
            require_tty(
                "Choosing a docker tag",
                hint="Pass --tag to set the tag non-interactively.",
            )
            tag = str(
                typer.prompt(
                    "The tag to use",
                    default=f"{username}/{build_model.manifest.identifier}:{build_model.manifest.version}-{build_model.flavour}",
                )
            )

        step(console, "Pushing docker container", escape(tag))

        if len(build_model.platforms) > 1:
            push_multi_arch(build_model, tag, work_dir, console)
        else:
            docker_run = subprocess.run(["docker", "tag", build_model.build_id, tag])
            if docker_run.returncode != 0:
                cli_error("Could not retag docker container")

            docker_run = subprocess.run(["docker", "push", tag])
            if docker_run.returncode != 0:
                cli_error("Could not push docker container")

        generate_deployment(
            deployment_run,
            build_model,
            tag,
            base_dir=work_dir,
        )

        done(console, f"Successfully pushed [bold]{escape(tag)}[/bold] to dockerhub")
        notice(
            console,
            "We have also generated a deployment file for you. Make sure to commit and "
            "push your changes to github to make them available to others.",
        )
