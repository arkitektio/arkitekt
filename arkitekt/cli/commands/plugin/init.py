"""The ``arkitekt plugin init`` command: scaffold a plugin flavour."""

from importlib.metadata import version
from typing import Annotated, Optional
from arkitekt.cli.validators import validate_dockerfile
from arkitekt.cli.errors import cli_error
from arkitekt.cli.tty import require_tty
from arkitekt.cli.utils import build_relative_dir
import typer
from arkitekt.cli.target import (
    DEFAULT_TARGET,
    TargetArgument,
    infer_package_manager,
    load_app_or_exit,
)
from arkitekt.cli.vars import get_console, get_work_dir
from arkitekt.utils import create_arkitekt_folder, create_devcontainer_file
from arkitekt.cli.ui import done, escape, notice

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


def _detect_template(work_dir: str) -> str:
    """Detect the correct dockerfile template from the project files.

    A uv project (a ``uv.lock``, or ``[tool.uv]`` in its pyproject) gets the uv
    image, which installs from the lockfile; anything else the pip-based one.
    """
    if infer_package_manager(work_dir) == "uv":
        return "uv"
    if os.path.exists(os.path.join(work_dir, "pyproject.toml")):
        with open(os.path.join(work_dir, "pyproject.toml")) as f:
            content = f.read()
        if "[tool.uv]" in content:
            return "uv"
    return "vanilla"


def write_flavour(
    work_dir: str,
    flavour: str = "vanilla",
    *,
    description: str = "This is a vanilla flavour",
    platforms: Optional[list[str]] = None,
    template: Optional[str] = None,
    arkitekt_version: Optional[str] = None,
    overwrite: bool = False,
) -> str:
    """Write a flavour's ``config.yaml`` and Dockerfile; return the Dockerfile's path.

    What ``plugin init`` does to the project, without its questions: ``create``
    writes a new project's first flavour through this too.

    Args:
        work_dir: The project.
        flavour: The flavour's name.
        description: What sets the flavour apart.
        platforms: What it builds for. Defaults to both architectures.
        template: The dockerfile template. Defaults to the one the project's
            package manager calls for.
        arkitekt_version: The arkitekt the pip-based image installs. Defaults to
            the one running.
        overwrite: Replace a flavour that exists.
    """
    import yaml
    from arkitekt.cli.commands.plugin.types import DEFAULT_PLATFORMS, Flavour

    arkitekt_folder = create_arkitekt_folder(base_dir=work_dir)

    flavour_folder = os.path.join(arkitekt_folder, "flavours", flavour)
    if os.path.exists(flavour_folder) and not overwrite:
        cli_error(
            f"The flavour {flavour} does already exist. Please initialize a different flavour or use the --overwrite flag"
        )
    os.makedirs(flavour_folder, exist_ok=True)

    config_file = os.path.join(flavour_folder, "config.yaml")
    dockerfile = os.path.join(flavour_folder, "Dockerfile")

    if template is None:
        template = _detect_template(work_dir)

    fl = Flavour(
        selectors=[],
        description=description,
        dockerfile="Dockerfile",
        platforms=list(platforms or DEFAULT_PLATFORMS),
    )

    try:
        package_version = arkitekt_version or version("arkitekt")
    except Exception:
        cli_error(
            "Could not detect the Arkitekt package version (maybe you are running a dev version). Please provide it with the --arkitekt-version flag"
        )

    with open(config_file, "w") as file:
        yaml.dump(fl.model_dump(), file)

    with open(build_relative_dir("dockerfiles", f"{template}.dockerfile"), "r") as f:
        dockerfile_content = f.read()

    with open(dockerfile, "w") as f:
        f.write(dockerfile_content.format(
            __arkitekt_version__=package_version,
            __python_version__=_detect_python_version(work_dir),
        ))

    return dockerfile


def init(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
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
            callback=validate_dockerfile,
        ),
    ] = None,
    devcontainer: Annotated[
        bool,
        typer.Option(
            "--devcontainer",
            "-dc",
            help="Should we create a devcontainer.json file?",
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
    platform: Annotated[
        Optional[list[str]],
        typer.Option(
            "--platform",
            "-p",
            help="The platforms this flavour builds for, e.g. -p linux/amd64 -p linux/arm64. "
            "Repeatable. Defaults to linux/amd64 and linux/arm64.",
        ),
    ] = None,
    no_multi_arch: Annotated[
        bool,
        typer.Option(
            "--no-multi-arch",
            help="Build only for this machine's architecture, as before multi-arch. "
            "Cross-building the other one needs emulation on the build host.",
        ),
    ] = False,
) -> None:
    """Initialize a plugin flavour for this app.

    Generates a Dockerfile and flavour ``config.yaml`` under
    ``.arkitekt/flavours/<flavour>`` so the app can be built and deployed as
    an Arkitekt plugin. Must be run inside an initialized app directory.
    """
    from arkitekt.cli.commands.plugin.buildx import host_platform
    from arkitekt.cli.commands.plugin.types import DEFAULT_PLATFORMS

    if platform and no_multi_arch:
        cli_error(
            "--platform and --no-multi-arch say different things about what to build. "
            "Pass the platforms you want, or --no-multi-arch for this machine's only."
        )

    if no_multi_arch:
        platforms = [host_platform()]
    elif platform:
        platforms = list(platform)
    else:
        platforms = list(DEFAULT_PLATFORMS)

    work_dir = get_work_dir(ctx)
    dockerfile = write_flavour(
        work_dir,
        flavour,
        description=description,
        platforms=platforms,
        template=template,
        arkitekt_version=arkitekt_version,
        overwrite=overwrite,
    )

    if not devcontainer:
        require_tty(
            "Choosing whether to create a devcontainer.json",
            hint="Pass --devcontainer to create it non-interactively.",
        )
    if devcontainer or typer.confirm("Do you want to create a devcontainer.json file?"):
        # Only the devcontainer is named after the app, so only it loads the app.
        app = load_app_or_exit(ctx, target)
        create_devcontainer_file(
            app, flavour, dockerfile, devcontainer_path=os.path.join(work_dir, ".devcontainer")
        )

    console = get_console(ctx)
    done(
        console,
        f"Created new flavour [bold]{escape(flavour)}[/bold]",
        f"builds for {escape(', '.join(platforms))} (change `platforms:` in its config.yaml)",
    )
    notice(console, "You can now edit the Dockerfile and add selectors to the config.yaml file")
    notice(
        console,
        "To learn more about selectors and how flavours work, please visit "
        "[link=https://arkitekt.live]https://arkitekt.live[/link]",
    )
