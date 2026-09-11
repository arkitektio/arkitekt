import sys
from typing import Annotated
from arkitekt_next.cli.errors import cli_error
from arkitekt_next.cli.vars import get_console, get_manifest, get_work_dir
import os
from rich.panel import Panel
import subprocess
import uuid

import typer
import json
from typing import Any, Dict, List, Optional
from arkitekt_next.constants import DEFAULT_ARKITEKT_URL


#: How long to let the in-container ``arkitekt-next inspect all`` run before
#: treating it as wedged. Without a bound, a container that never emits the
#: ``--END_AGENT--`` sentinel (or hangs on import) would block the build forever.
INSPECTION_TIMEOUT_SECONDS = 300


class InspectionError(Exception):
    pass


def build_flavour(flavour_name: str, flavour: "Flavour", work_dir: str) -> str:
    """Builds a flavour to a Docker image and returns the build_id (tag)."""
    build_id = str(uuid.uuid4())
    relative_dir = os.path.join(".arkitekt_next", "flavours", flavour_name, "")
    command = flavour.generate_build_command(build_id, relative_dir)
    docker_run = subprocess.run(" ".join(command), shell=True, cwd=work_dir)
    if docker_run.returncode != 0:
        cli_error("Could not build docker container")
    return build_id


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


def inspect_all(build_id: str, url: str) -> Dict[str, Any]:
    try:
        # No ``-it``: a TTY is meaningless when stdout/stderr are piped and it
        # keeps the read from cleanly ending on container exit.
        process = subprocess.Popen(
            " ".join([
                "docker", "run", "--network", "host",
                build_id, "arkitekt-next", "inspect", "all", "-mr",
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
                "`arkitekt-next inspect all` returns inside the image."
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
                "Running `arkitekt-next inspect all` inside the container failed."
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
                "Command `arkitekt-next inspect implementations` not found in container. "
                "Did you forget to install arkitekt-next?"
            )
        raise InspectionError(f"An error occurred: {combined}") from e


def inspect_requirements(build_id: str) -> "List[RequirementInput]":
    try:
        result = subprocess.run(
            ["docker", "run", build_id, "arkitekt-next", "inspect", "requirements", "-mr"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
        correct_part = result.stdout.split("--START_REQUIREMENTS--")[1].split(
            "--END_REQUIREMENTS--"
        )[0]
        try:
            return json.loads(correct_part)
        except json.decoder.JSONDecodeError as e:
            raise InspectionError(
                f"Could not decode requirements JSON. {result.stdout + result.stderr}"
            ) from e
    except subprocess.CalledProcessError as e:
        combined = e.stdout + e.stderr
        if "No such command" in combined:
            raise InspectionError(
                "Command `arkitekt-next inspect requirements` not found in container."
            )
        raise InspectionError(f"An error occurred: {combined}") from e


def inspect_build(build_id: str, url: str) -> "InspectionInput":
    from .types import InspectionInput

    size, size_root_fs = inspect_docker_container(build_id)
    runtime = inspect_all(build_id, url)
    print("Runtime inspection result:", runtime)
    return InspectionInput(size=size, **runtime)


def build(
    ctx: typer.Context,
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
        typer.Option("--tag", "-t", help="Tag the build with a specific tag."),
    ] = None,
    url: Annotated[
        str,
        typer.Option("--url", "-u", help="The fakts-next server to use."),
    ] = DEFAULT_ARKITEKT_URL,
) -> None:
    """Builds the arkitekt-next app to Docker."""
    from .io import generate_build, get_flavours

    manifest = get_manifest(ctx)
    console = get_console(ctx)
    work_dir = get_work_dir(ctx)

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

        build_tag = build_flavour(key, inspected_flavour, work_dir)

        if tag:
            subprocess.run(["docker", "tag", build_tag, tag], check=True)

        inspection = None
        if not no_inspect:
            inspection = inspect_build(build_tag, url)

        generate_build(build_run, build_tag, key, inspected_flavour, manifest, inspection, base_dir=work_dir)

        console.print(Panel(
            "Built Flavour [bold]{}[/bold]".format(key),
            subtitle="Build ID: {}".format(build_run),
            subtitle_align="right",
        ))
