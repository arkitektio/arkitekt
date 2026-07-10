"""The ``arkitekt-next self upgrade`` command.

Checks PyPI for the latest version of every installed Arkitekt ecosystem package
and upgrades the outdated ones using the project's package manager (``uv`` or
``pip``).
"""

import enum
import sys
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from importlib.metadata import version as installed_version, PackageNotFoundError
from typing import Annotated, List, Optional, Tuple

import typer
import semver
from rich.table import Table

from arkitekt_next.cli.errors import cli_error, confirm_or_abort
from arkitekt_next.cli.interactive import require_interactive
from arkitekt_next.cli.vars import get_console, get_work_dir
from arkitekt_next.cli.commands.app.init.main import get_default_package_manager
from .constants import ARKITEKT_PACKAGES

PYPI_JSON_URL = "https://pypi.org/pypi/{name}/json"


class PackageManager(str, enum.Enum):
    """The package managers supported by ``self upgrade``."""

    pip = "pip"
    uv = "uv"


def _resolve_package_manager(ctx, package_manager: Optional[PackageManager]) -> str:
    """Resolve which package manager to use.

    Explicit ``--package-manager`` wins, otherwise fall back to the loaded
    manifest's ``package_manager`` (if a manifest was found), otherwise auto
    detect (``uv`` if available, else ``pip``).
    """
    if package_manager:
        return package_manager.value

    manifest = ctx.obj.get("manifest") if ctx.obj else None
    if manifest is not None:
        return manifest.package_manager

    return get_default_package_manager()


def _fetch_latest_version(name: str, pre: bool) -> Optional[str]:
    """Return the latest version of ``name`` on PyPI, or ``None`` on failure.

    When ``pre`` is False the latest stable release is returned (PyPI's
    ``info.version`` already points at the latest stable). When ``pre`` is True
    the highest release overall (including pre-releases) is returned.
    """
    try:
        with urllib.request.urlopen(
            PYPI_JSON_URL.format(name=name), timeout=10.0
        ) as response:
            data = json.load(response)
    except (urllib.error.URLError, ValueError, TimeoutError):
        return None

    if not pre:
        return data.get("info", {}).get("version")

    releases = list(data.get("releases", {}).keys())
    highest: Optional[str] = None
    for candidate in releases:
        try:
            if highest is None or semver.Version.parse(candidate).compare(highest) > 0:
                highest = candidate
        except ValueError:
            continue
    return highest or data.get("info", {}).get("version")


def _is_newer(latest: str, current: str) -> bool:
    """Whether ``latest`` is a strictly newer version than ``current``."""
    try:
        return semver.Version.parse(latest).compare(current) > 0
    except ValueError:
        # Fall back to a plain string comparison for non-semver versions.
        return latest != current


def _upgrade_all_dependencies(ctx, console, manager: str, yes: bool) -> None:
    """Upgrade *every* dependency of the current project (not just Arkitekt ones).

    For ``uv`` this runs ``uv sync --upgrade``, which upgrades all packages to the
    latest versions allowed by ``pyproject.toml`` and rewrites the lockfile. For
    ``pip`` it upgrades every outdated top-level distribution reported by
    ``pip list --outdated``.
    """
    if manager == "uv":
        if not shutil.which("uv"):
            cli_error(
                "uv is not installed. Please install uv or choose --package-manager pip."
            )
        if not yes:
            require_interactive("Confirming the upgrade", hint="Pass --yes to upgrade non-interactively.")
            confirm_or_abort(
                "Upgrade ALL project dependencies with `uv sync --upgrade`?",
            )
        command = ["uv", "sync", "--upgrade"]
        console.print(f"Running: {' '.join(command)}", style="cyan")
        try:
            subprocess.run(command, check=True, cwd=get_work_dir(ctx))
        except subprocess.CalledProcessError as e:
            cli_error(f"Failed to upgrade dependencies (exit code {e.returncode}).")
        console.print("Successfully upgraded all project dependencies. 🚀", style="green")
        return

    # pip: discover outdated distributions and upgrade them.
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
            check=True,
            capture_output=True,
            text=True,
        )
        outdated_names = [entry["name"] for entry in json.loads(proc.stdout or "[]")]
    except (subprocess.CalledProcessError, ValueError) as e:
        cli_error(f"Could not determine outdated packages via pip: {e}")

    if not outdated_names:
        console.print("Everything is up to date. 🎉", style="green")
        return

    console.print(f"{len(outdated_names)} outdated package(s): {', '.join(outdated_names)}")
    if not yes:
        require_interactive("Confirming the upgrade", hint="Pass --yes to upgrade non-interactively.")
        confirm_or_abort(f"Upgrade all {len(outdated_names)} package(s) with pip?")

    command = [sys.executable, "-m", "pip", "install", "--upgrade", *outdated_names]
    console.print(f"Running: {' '.join(command)}", style="cyan")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        cli_error(f"Failed to upgrade dependencies (exit code {e.returncode}).")
    console.print("Successfully upgraded all project dependencies. 🚀", style="green")


def upgrade(
    ctx: typer.Context,
    package_manager: Annotated[
        Optional[PackageManager],
        typer.Option(
            "--package-manager",
            "-pm",
            help="The package manager to use for the upgrade. Defaults to the project manifest's package manager, or auto-detected (uv if available, else pip).",
        ),
    ] = None,
    upgrade_all: Annotated[
        bool,
        typer.Option(
            "--all",
            "-a",
            help="Upgrade ALL dependencies of the current project, not just the Arkitekt ecosystem packages.",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Skip the confirmation prompt and upgrade immediately.",
        ),
    ] = False,
    pre: Annotated[
        bool,
        typer.Option(
            "--pre",
            help="Allow upgrading to pre-release versions.",
        ),
    ] = False,
) -> None:
    """Upgrade the installed Arkitekt SDK packages to their latest PyPI version.

    Checks [link=https://pypi.org]PyPI[/link] for the latest version of every
    installed Arkitekt ecosystem package (arkitekt-next, rekuest-next,
    mikro-next, fakts-next, ...) and upgrades the outdated ones using your
    project's package manager. Pass `--all` to upgrade *every* dependency of the
    current project instead. Only `uv` and `pip` are supported.
    """
    console = get_console(ctx)

    if upgrade_all:
        manager = _resolve_package_manager(ctx, package_manager)
        _upgrade_all_dependencies(ctx, console, manager, yes)
        return

    console.print("Checking PyPI for the latest versions...", style="cyan")

    outdated: List[Tuple[str, str, str]] = []  # (name, current, latest)
    for name in ARKITEKT_PACKAGES:
        try:
            current = installed_version(name)
        except PackageNotFoundError:
            # Not installed in this environment — nothing to upgrade.
            continue

        latest = _fetch_latest_version(name, pre)
        if latest is None:
            console.print(
                f"Could not fetch the latest version for {name}, skipping.",
                style="yellow",
            )
            continue

        if _is_newer(latest, current):
            outdated.append((name, current, latest))

    if not outdated:
        console.print("Everything is up to date. 🎉", style="green")
        return

    table = Table(title="Available upgrades")
    table.add_column("Package", style="bold")
    table.add_column("Installed", style="red")
    table.add_column("Latest", style="green")
    for name, current, latest in outdated:
        table.add_row(name, current, latest)
    console.print(table)

    manager = _resolve_package_manager(ctx, package_manager)

    if not yes:
        require_interactive("Confirming the upgrade", hint="Pass --yes to upgrade non-interactively.")
        confirm_or_abort(
            f"Upgrade {len(outdated)} package(s) using {manager}?",
        )

    packages = [name for name, _, _ in outdated]

    if manager == "uv":
        if not shutil.which("uv"):
            cli_error(
                "uv is not installed. Please install uv or choose another package manager with --package-manager pip."
            )
        command = ["uv", "add", "--upgrade", *packages]
        cwd = get_work_dir(ctx)
    else:
        command = [sys.executable, "-m", "pip", "install", "--upgrade", *packages]
        cwd = None

    console.print(f"Running: {' '.join(command)}", style="cyan")
    try:
        subprocess.run(command, check=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        cli_error(
            f"Failed to upgrade packages (exit code {e.returncode})."
        )

    console.print("Successfully upgraded the Arkitekt packages. 🚀", style="green")
