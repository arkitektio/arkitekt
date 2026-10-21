import sys
from typing import Annotated
from arkitekt.cli.errors import cli_error
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument
from arkitekt.cli.vars import get_console, get_work_dir
import os
import shlex
from arkitekt.cli.ui import done, escape, notice, step
import subprocess
import uuid

import typer
import json
from typing import TYPE_CHECKING, Any, Dict, Optional
from arkitekt.constants import DEFAULT_ARKITEKT_URL

if TYPE_CHECKING:
    from arkitekt_spec import AppManifest, Inspection

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
        build_host_image(build_id, flavour_name, flavour, work_dir, wanted, console=console)
        return build_id

    build_host_image(build_id, flavour_name, flavour, work_dir, wanted, console=console)

    host = host_platform()
    builder = ensure_builder(wanted, console=console)
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


def build_host_image(
    build_id: str,
    flavour_name: str,
    flavour: "Flavour",
    work_dir: str,
    platforms: list[str],
    console: Any = None,
) -> None:
    """Build this machine's image of a flavour into the local image store, as ``build_id``.

    That image is the one that can be run here, so it is the one that says what
    the app is. It is built with the builder the whole platform list needs, so a
    later build of all of them (``publish``, ``release``) reuses its layers.
    """
    from .buildx import ensure_builder, host_platform

    relative_dir = flavour_relative_dir(flavour_name)

    if flavour.is_customized():
        _run_build(flavour.generate_build_command(build_id, relative_dir), work_dir, "build")
        return

    host = host_platform()
    builder = ensure_builder(platforms, console=console)

    if host not in platforms:
        # Nothing would be left in the local image store, and every step after
        # this one (inspection, --tag, stage) reads it.
        cli_error(
            f"Flavour {flavour_name} builds {', '.join(platforms)}, none of which is this "
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


def inspect_all(
    build_id: str, url: str, target: str = DEFAULT_TARGET
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Run ``arkitekt inspect all`` on ``target`` inside the built image.

    Returns what the image declares (its ``AGENT``) and who it says it is (its
    ``MANIFEST``). Both come from the image, not from the source on this machine:
    the image is what runs, and a flavour may well hold another app than the host has.

    The target is passed explicitly: the image has to be inspected on the app it
    was built for, which need not be the default ``app``.
    """
    try:
        # No ``-it``: a TTY is meaningless when stdout/stderr are piped and it
        # keeps the read from cleanly ending on container exit.
        process = subprocess.Popen(
            " ".join([
                "docker", "run", "--rm", "--network", "host",
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

        runtime = machine_readable(result, "AGENT")
        if runtime is None:
            raise InspectionError(f"The container reported no inspection. {result}")
        manifest = machine_readable(result, "MANIFEST")
        if manifest is None:
            raise InspectionError(
                "The container did not say which app it is (no MANIFEST in its inspection). "
                "Its arkitekt predates that: the image has to install arkitekt 6.2.0 or newer."
            )
        return runtime, manifest

    except subprocess.CalledProcessError as e:
        combined = e.stdout + e.stderr
        if "No such command" in combined:
            raise InspectionError(
                "Command `arkitekt inspect implementations` not found in container. "
                "Did you forget to install arkitekt?"
            )
        raise InspectionError(f"An error occurred: {combined}") from e


def machine_readable(output: str, kind: str) -> Optional[Dict[str, Any]]:
    """The ``--START_<KIND>--``/``--END_<KIND>--`` payload in a command's output, if any."""
    _, start, rest = output.partition(f"--START_{kind}--")
    payload, end, _ = rest.partition(f"--END_{kind}--")
    if not start or not end:
        return None
    try:
        return json.loads(payload)
    except json.decoder.JSONDecodeError as e:
        raise InspectionError(f"Could not decode the {kind} JSON. {output}") from e


def inspect_build(
    build_id: str, url: str, target: str = DEFAULT_TARGET
) -> tuple["Inspection", "AppManifest"]:
    """What a built image declares, and who it says it is."""
    from arkitekt_spec import AppManifest, Inspection

    size, size_root_fs = inspect_docker_container(build_id)
    runtime, manifest = inspect_all(build_id, url, target)
    print("Runtime inspection result:", runtime)
    return (
        Inspection.model_validate({**runtime, "size": size}),
        AppManifest.model_validate(manifest),
    )


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
        typer.Option(
            "--no-inspect",
            "-n",
            help="Only build: do not run the image. Without its inspection nothing says "
            "which app it holds, so the build is not recorded for stage or publish.",
        ),
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

    Everything recorded about a build is read from the built image: what it
    declares, and the app's identity (identifier, version, author, scopes, logo).
    The app is never imported on this machine, so building needs docker, not the
    app's dependencies.
    """
    from .io import generate_build, get_flavours

    console = get_console(ctx)
    work_dir = get_work_dir(ctx)

    flavours = get_flavours(base_dir=work_dir, select=flavour)

    step(
        console,
        f"Building containers for [bold]{escape(target)}[/bold]",
        "flavours: " + escape(", ".join(flavours.keys())),
    )

    build_run = str(uuid.uuid4())

    for key, inspected_flavour in flavours.items():
        step(console, f"Building flavour [bold]{escape(key)}[/bold]", "this may take a while...")

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

        if no_inspect:
            done(console, f"Built flavour [bold]{escape(key)}[/bold]", f"image {build_tag}")
            notice(
                console,
                "Not recorded",
                "built with --no-inspect, so nothing says which app the image holds",
            )
            continue

        try:
            inspection, manifest = inspect_build(build_tag, url, target)
        except InspectionError as error:
            cli_error(str(error))

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

        done(
            console,
            f"Built flavour [bold]{escape(key)}[/bold]",
            f"{escape(manifest.identifier)} {escape(manifest.version)} · build {build_run}",
        )
