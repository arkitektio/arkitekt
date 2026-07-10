"""The ``arkitekt-next plugin init`` command: scaffold a plugin flavour."""

from importlib.metadata import version
from typing import Annotated, Optional
from arkitekt_next.cli.constants import compile_dockerfiles
from arkitekt_next.cli.errors import cli_error
from arkitekt_next.cli.interactive import require_interactive
from arkitekt_next.cli.utils import build_relative_dir
import typer
from arkitekt_next.cli.vars import get_console, get_manifest, get_work_dir
from arkitekt_next.utils import create_arkitekt_next_folder, create_devcontainer_file
from rich.panel import Panel

try:
    pass
except ImportError as e:
    raise ImportError("Please install rekuest to use this feature") from e

import os
import re
import sys


def _detect_python_version(work_dir: str) -> str:
    """Detect the Python version for the project, returning 'major.minor' (e.g. '3.12').

    Priority:
    1. .python-version file (created by uv/pyenv)
    2. requires-python in pyproject.toml (takes minimum bound)
    3. Current interpreter version
    """
    python_version_file = os.path.join(work_dir, ".python-version")
    if os.path.exists(python_version_file):
        with open(python_version_file) as f:
            raw = f.read().strip()
        parts = raw.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        if len(parts) == 1 and parts[0].isdigit():
            return raw

    pyproject = os.path.join(work_dir, "pyproject.toml")
    if os.path.exists(pyproject):
        with open(pyproject) as f:
            content = f.read()
        match = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            specifier = match.group(1)
            version_match = re.search(r"(\d+\.\d+)", specifier)
            if version_match:
                return version_match.group(1)

    return f"{sys.version_info.major}.{sys.version_info.minor}"


def _detect_template(work_dir: str, manifest_package_manager: str) -> str:
    """Detect the correct dockerfile template from project files, falling back to the manifest."""
    if os.path.exists(os.path.join(work_dir, "uv.lock")):
        return "uv"
    if os.path.exists(os.path.join(work_dir, "pyproject.toml")):
        with open(os.path.join(work_dir, "pyproject.toml")) as f:
            content = f.read()
        if "[tool.uv]" in content:
            return "uv"
    if manifest_package_manager == "uv":
        return "uv"
    return "vanilla"


def _validate_template(value: Optional[str]) -> Optional[str]:
    """Validate ``--template`` against the dockerfile templates available at call time."""
    if value is None:
        return value
    choices = compile_dockerfiles()
    if value not in choices:
        raise typer.BadParameter(
            f"{value!r} is not one of {', '.join(choices)}."
        )
    return value


def init(
    ctx: typer.Context,
    flavour: Annotated[
        str, typer.Option("--flavour", "-f", help="The flavour to use")
    ] = "vanilla",
    description: Annotated[
        str,
        typer.Option(
            "--description", "-d", help="The description for this flavour to use"
        ),
    ] = "This is a vanilla flavour",
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite", "-o", help="Should we overwrite the existing Dockerfile?"
        ),
    ] = False,
    template: Annotated[
        Optional[str],
        typer.Option(
            "--template",
            "-t",
            help="The dockerfile template to use",
            callback=_validate_template,
        ),
    ] = None,
    devcontainer: Annotated[
        bool,
        typer.Option(
            "--devcontainer",
            "-dc",
            help="Shouwld we create a devcontainer.json file?",
        ),
    ] = False,
    arkitekt_version: Annotated[
        Optional[str],
        typer.Option(
            "--arkitekt-version",
            "-av",
            help="Which Arkitekt-version should we use to mount in the container?",
        ),
    ] = None,
) -> None:
    """Initialize a plugin flavour for this app.

    Generates a Dockerfile and flavour ``config.yaml`` under
    ``.arkitekt_next/flavours/<flavour>`` so the app can be built and deployed as
    an Arkitekt plugin. Must be run inside an initialized app directory.
    """
    import yaml
    from arkitekt_next.cli.commands.plugin.types import Flavour

    work_dir = get_work_dir(ctx)
    arkitekt_next_folder = create_arkitekt_next_folder(base_dir=work_dir)

    flavour_folder = os.path.join(arkitekt_next_folder, "flavours", flavour)
    if os.path.exists(flavour_folder) and not overwrite:
        cli_error(
            f"The flavour {flavour} does already exist. Please initialize a different flavour or use the --overwrite flag"
        )
    else:
        os.makedirs(flavour_folder, exist_ok=True)

    config_file = os.path.join(flavour_folder, "config.yaml")
    dockerfile = os.path.join(flavour_folder, "Dockerfile")

    manifest = get_manifest(ctx)

    if template is None:
        template = _detect_template(work_dir, manifest.package_manager)

    fl = Flavour(
        selectors=[],
        description=description,
        dockerfile="Dockerfile",
    )

    try:
        package_version = arkitekt_version or version("arkitekt_next")
        print(f"Detected Arkitekt Package version: {package_version}")
    except Exception:
        cli_error(
            "Could not detect the Arkitekt package version (maybe you are running a dev version). Please provide it with the --arkitekt-version flag"
        )

    with open(config_file, "w") as file:
            yaml.dump(fl.model_dump(), file)

    python_version = _detect_python_version(work_dir)
    print(f"Detected Python version: {python_version}")

    with open(build_relative_dir("dockerfiles", f"{template}.dockerfile"), "r") as f:
        dockerfile_content = f.read()

    with open(dockerfile, "w") as f:
        f.write(dockerfile_content.format(
            __arkitekt_version__=package_version,
            __python_version__=python_version,
        ))

    if not devcontainer:
        require_interactive(
            "Choosing whether to create a devcontainer.json",
            hint="Pass --devcontainer to create it non-interactively.",
        )
    if devcontainer or typer.confirm("Do you want to create a devcontainer.json file?"):
        create_devcontainer_file(manifest, flavour, dockerfile)

    panel = Panel(
        title=f"Created new flavour [bold]{flavour}[/bold]\n",
        renderable="You can now edit the Dockerfile and add selectors to the config.yaml file\n"
        + "To learn more about selectors and how flavours work, please visit [link=https://arkitekt.live]https://arkitekt.live[/link]",
        style="green",
    )

    get_console(ctx).print(panel)
