import sys
from typing import Annotated
from arkitekt.cli.errors import cli_error
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.vars import get_console, get_work_dir
import os
import shlex
from rich.panel import Panel
import subprocess
import uuid

import typer
import json
from typing import TYPE_CHECKING, Any, Dict, Optional
from arkitekt.constants import DEFAULT_ARKITEKT_URL

if TYPE_CHECKING:
    from arkitekt_spec import Inspection

    from .types import Flavour


#: How long to let the in-container ``arkitekt inspect all`` run before
#: treating it as wedged. Without a bound, a container that never emits the
#: ``--END_AGENT--`` sentinel (or hangs on import) would block the build forever.
INSPECTION_TIMEOUT_SECONDS = 300


class InspectionError(Exception):
    pass


def flavour_relative_dir(flavour_name: str) -> str:
    """Where a flavour's Dockerfile lives, relative to the work dir."""
    return os.path.join(".arkitekt", "flavours", flavour_name, "")


def build_flavour(
    flavour_name: str,
    flavour: "Flavour",
    work_dir: str,
    platforms: Optional[list[str]] = None,
    console: Any = None,
) -> str:
    """Build a flavour for every platform it targets; return the build_id (tag).

    A manifest list cannot live in the local image store, so the platforms are
    built in two passes: the host one is ``--load``ed, which is the image that
    then gets inspected, staged and optionally retagged, and the rest are built
    to the builder's cache. Nothing is exported for them here — they are pushed
    as one manifest list by ``plugin publish``, which reuses this cache.

    Building the foreign platforms now rather than at publish time is the point:
    a dependency with no arm64 wheel fails here, next to the code that caused it.
    """
    from .buildx import ensure_builder, host_platform

    build_id = str(uuid.uuid4())
    relative_dir = flavour_relative_dir(flavour_name)
    wanted = list(dict.fromkeys(platforms if platforms is not None else flavour.platforms))

    if flavour.is_customized():
        # A hand-written command is run as written; this CLI has nowhere to put
        # the platform flags in it. Say so when the config claims more, instead
        # of quietly building one architecture for a flavour that promises two.
        if len(wanted) > 1 and console:
            console.print(
                f"[yellow]Flavour [bold]{flavour_name}[/bold] sets its own build_command, so it "
                f"builds for this machine only — but its platforms say {', '.join(wanted)}. "
                "Drop build_command from its config.yaml to build them all.[/yellow]"
            )
        _run_build(flavour.generate_build_command(build_id, relative_dir), work_dir, "build")
        return build_id

    host = host_platform()
    builder = ensure_builder(wanted, console=console)

    if host not in wanted:
        # Nothing would be left in the local image store, and every step after
        # this one (inspection, --tag, stage) reads it.
        cli_error(
            f"Flavour {flavour_name} builds {', '.join(wanted)}, none of which is this "
            f"machine's platform ({host}), so nothing can be loaded, inspected or staged "
            "locally. Add it to `platforms:` in the flavour's config.yaml."
        )

    _run_build(
        flavour.generate_build_command(
            build_id, relative_dir, platform=host, output="--load", builder=builder
        ),
        work_dir,
        f"build for {host}",
    )

    foreign = [p for p in wanted if p != host]
    if foreign:
        if console:
            console.print(f"Building for {', '.join(foreign)}...")
        _run_build(
            flavour.generate_build_command(
                build_id,
                relative_dir,
                platform=",".join(foreign),
                # Not exported: a multi-platform result cannot be loaded, and the
                # cache this leaves is what publish pushes from.
                output="--output=type=cacheonly",
                builder=builder,
            ),
            work_dir,
            f"build for {', '.join(foreign)}",
        )

    return build_id


def _run_build(command: list[str], work_dir: str, what: str) -> None:
    """Run one docker build, naming which pass failed.

    Argv form, not ``shell=True``: platform strings come out of a config file
    and have no business being re-parsed by a shell.
    """
    docker_run = subprocess.run(command, cwd=work_dir)
    if docker_run.returncode != 0:
        cli_error(f"Could not {what} (`{' '.join(command)}` failed)")


def inspect_docker_container(build_id: str) -> tuple[int, int]:
    try:
        result = subprocess.run(
            ["docker", "inspect", build_id],
            stdout=subprocess.PIPE,
            text=True,
            check=True,
        )
        try:
            container_info = json.loads(result.stdout)
        except json.decoder.JSONDecodeError as e:
            raise InspectionError(
                f"Could not decode JSON output of docker inspect. {result.stdout}"
            ) from e
        try:
            size = container_info[0]["Size"]
            size_root_fs = container_info[0]["Size"]
        except (IndexError, KeyError) as e:
            raise InspectionError("Size information not found in container details") from e
        return size, size_root_fs
    except subprocess.CalledProcessError as e:
        raise InspectionError(f"An error occurred: {e.stdout}{e.stderr}") from e


def inspect_all(build_id: str, url: str, target: str = DEFAULT_TARGET) -> Dict[str, Any]:
    """Run ``arkitekt inspect all`` on ``target`` inside the built image.

    The target is passed explicitly: the image has to be inspected on the app it
    was built for, which need not be the default ``app``.
    """
    try:
        # No ``-it``: a TTY is meaningless when stdout/stderr are piped and it
        # keeps the read from cleanly ending on container exit.
        process = subprocess.Popen(
            " ".join([
                "docker", "run", "--network", "host",
                build_id, "arkitekt", "inspect", "all", shlex.quote(target), "-mr",
            ]),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # ``communicate`` reads to EOF but is bounded by ``timeout`` -- a wedged
        # container is killed and reported rather than hanging the build forever.
        try:
            stdout, _stderr = process.communicate(timeout=INSPECTION_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise InspectionError(
                f"Inspecting the container ({build_id}) timed out after "
                f"{INSPECTION_TIMEOUT_SECONDS}s and was aborted. Make sure "
                "`arkitekt inspect all` returns inside the image."
            )

        # Surface the captured output so the operator still sees what ran.
        if stdout:
            sys.stdout.buffer.write(stdout)
            sys.stdout.flush()
        result = stdout.decode("utf-8")

        if process.returncode != 0:
            if "ModuleNotFoundError" in result:
                cli_error(
                    "Missing a module in the container. Make sure all dependencies are installed."
                )
            cli_error(
                "Running `arkitekt inspect all` inside the container failed."
            )

        correct_part = result.split("--START_AGENT--")[1].split("--END_AGENT--")[0]
        try:
            return json.loads(correct_part)
        except json.decoder.JSONDecodeError as e:
            raise InspectionError(f"Could not decode inspection JSON. {result}") from e

    except subprocess.CalledProcessError as e:
        combined = e.stdout + e.stderr
        if "No such command" in combined:
            raise InspectionError(
                "Command `arkitekt inspect implementations` not found in container. "
                "Did you forget to install arkitekt?"
            )
        raise InspectionError(f"An error occurred: {combined}") from e


def inspect_build(build_id: str, url: str, target: str = DEFAULT_TARGET) -> "Inspection":
    from arkitekt_spec import Inspection

    size, size_root_fs = inspect_docker_container(build_id)
    runtime = inspect_all(build_id, url, target)
    print("Runtime inspection result:", runtime)
    return Inspection.model_validate({**runtime, "size": size})


def build(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    flavour: Annotated[
        Optional[str],
        typer.Option(
            "--flavour",
            "-f",
            help="The flavour to build. By default all flavours are built.",
        ),
    ] = None,
    no_inspect: Annotated[
        bool,
        typer.Option("--no-inspect", "-n", help="Skip inspection of the app."),
    ] = False,
    tag: Annotated[
        Optional[str],
        typer.Option(
            "--tag",
            "-t",
            help="Tag the build with a specific tag. Only this machine's architecture "
            "is tagged; `arkitekt plugin publish` is what pushes a multi-arch image.",
        ),
    ] = None,
    platform: Annotated[
        Optional[list[str]],
        typer.Option(
            "--platform",
            "-p",
            help="Build for these platforms instead of the ones the flavour declares, "
            "e.g. -p linux/amd64. Repeatable.",
        ),
    ] = None,
    url: Annotated[
        str,
        typer.Option("--url", "-u", help="The fakts server to use."),
    ] = DEFAULT_ARKITEKT_URL,
) -> None:
    """Builds the arkitekt app to Docker.

    The app's identity (identifier, version, author, scopes, logo) is read off the
    App the target declares and recorded with each build.
    """
    from .io import app_to_manifest, generate_build, get_flavours

    console = get_console(ctx)
    work_dir = get_work_dir(ctx)
    app = load_app_or_exit(ctx, target)
    manifest = app_to_manifest(app, target)

    flavours = get_flavours(base_dir=work_dir, select=flavour)

    console.print(Panel(
        "Starting to Build Containers for App [bold]{}[/bold]".format(manifest.identifier),
        subtitle="Selected Flavours: {}".format(", ".join(flavours.keys())),
    ))

    build_run = str(uuid.uuid4())

    for key, inspected_flavour in flavours.items():
        console.print(Panel(
            "Building Flavour [bold]{}[/bold]".format(key),
            subtitle="This may take a while...",
            subtitle_align="right",
        ))

        platforms = list(platform) if platform else list(inspected_flavour.platforms)

        build_tag = build_flavour(
            key, inspected_flavour, work_dir, platforms=platforms, console=console
        )

        if tag:
            if len(platforms) > 1:
                console.print(
                    f"[yellow]--tag names the {len(platforms)}-platform flavour's image for this "
                    "machine only; pushing that tag by hand publishes one architecture. "
                    "`arkitekt plugin publish` pushes the manifest list.[/yellow]"
                )
            subprocess.run(["docker", "tag", build_tag, tag], check=True)

        inspection = None
        if not no_inspect:
            inspection = inspect_build(build_tag, url, target)

        generate_build(
            build_run,
            build_tag,
            key,
            inspected_flavour,
            manifest,
            inspection,
            base_dir=work_dir,
            platforms=platforms,
        )

        console.print(Panel(
            "Built Flavour [bold]{}[/bold]".format(key),
            subtitle="Build ID: {}".format(build_run),
            subtitle_align="right",
        ))
