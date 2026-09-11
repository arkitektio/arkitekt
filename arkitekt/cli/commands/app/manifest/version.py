from typing import Annotated, Optional

import typer
from semver import Version
from arkitekt.cli.interactive import require_interactive
from arkitekt.cli.vars import get_console, get_manifest, get_work_dir
from arkitekt.cli.io import write_manifest


version = typer.Typer(
    no_args_is_help=True,
    help="""Updates the version of the arkitekt app

    ArkitektNext manifests versioning follow [link=https://semver.org]semver[/link] and are used to version the app.
    This provides an orthogonal way to version the app, beyond node versioning. The version is used to
    track changes and to provide a way to update the app in the platform. For more information, please visit
    [link=https://arkitekt.live]https://arkitekt.live[/link]

    """,
)


def set_version(
    ctx: typer.Context,
    version: Annotated[Optional[str], typer.Argument()] = None,
) -> None:
    """Sets the version of the arkitekt app

    When setting the version, you can either provide a version, or you can let the cli
    prompt you for a version. If you provide a version, it will be parsed and validated
    against semver. If you let the cli prompt you, it will try to parse the current version
    and suggest a new version based on that. If the current version is not a valid semver
    version, it will prompt you for a new version without a suggestion.
    """

    manifest = get_manifest(ctx)
    console = get_console(ctx)
    work_dir = get_work_dir(ctx)
    old_version = manifest.version

    if not version:
        require_interactive(
            "Choosing a new version",
            hint="Pass the version as an argument to set it non-interactively.",
        )
        try:
            potential_new_version = str(Version.parse(old_version).bump_patch())
        except Exception:
            potential_new_version = None

        new_version = typer.prompt(
            "Please provide a new version", default=potential_new_version, type=str
        )
        Version.parse(new_version)
        version = new_version

    manifest.version = version
    write_manifest(manifest, base_dir=work_dir)
    console.print(f"Version Updated from {old_version} to {version}")


def patch(ctx: typer.Context) -> None:
    """ "Patches the version of the arkitekt app


    Patches the version of the arkitekt app, by bumping the patch number.
    E.g. from 1.0.1 to 1.0.2. This should be used for bugfixes and small changes.
    """
    manifest = get_manifest(ctx)
    console = get_console(ctx)
    old_version = manifest.version
    manifest.version = str(Version.parse(old_version).bump_patch())
    write_manifest(manifest, base_dir=get_work_dir(ctx))
    console.print(f"Version Updated from {old_version} to {manifest.version}")


def minor(ctx: typer.Context) -> None:
    """Bumps the minor version number of the arkitekt app

    Patches the version of the arkitekt app, by bumping the minor number.
    E.g. from 1.0.1 to 1.1.1. This should be used for new features, that
    are backwards compatible.

    """
    manifest = get_manifest(ctx)
    console = get_console(ctx)
    old_version = manifest.version
    manifest.version = str(Version.parse(old_version).bump_minor())
    write_manifest(manifest, base_dir=get_work_dir(ctx))
    console.print(f"Version Updated from {old_version} to {manifest.version}")


def major(ctx: typer.Context) -> None:
    """Increase the major version of the arkitekt app"

    Patches the version of the arkitekt app, by bumping the major number.
    E.g. from 1.0.1 to 2.0.1, This should be used for breaking changes,
    that are not backwards compatible (e.g. deleting a node).

    """
    manifest = get_manifest(ctx)
    console = get_console(ctx)
    old_version = manifest.version
    manifest.version = str(Version.parse(old_version).bump_major())
    write_manifest(manifest, base_dir=get_work_dir(ctx))
    console.print(f"Version Updated from {old_version} to {manifest.version}")


def prerelease(ctx: typer.Context) -> None:
    """Patches the prerelease of the arkitekt app"


    Patches the version of the arkitekt app, by bumping the prerelease number.
    E.g. from 1.0.1 to 1.0.1-alpha.1
    """
    manifest = get_manifest(ctx)
    console = get_console(ctx)
    old_version = manifest.version
    manifest.version = str(Version.parse(old_version).bump_prerelease())
    write_manifest(manifest, base_dir=get_work_dir(ctx))
    console.print(f"Version Updated from {old_version} to {manifest.version}")


def build_version(ctx: typer.Context) -> None:
    """Patches the build of the arkitekt app

    Patches the version of the arkitekt app, by bumping the build number.
    E.g. from 1.0.1 to 1.0.1+1, This should be used for changes that are not
    reflected in the version number, but are still important to track (e.g. a
    hotfix).

    """
    manifest = get_manifest(ctx)
    console = get_console(ctx)
    old_version = manifest.version
    manifest.version = str(Version.parse(old_version).bump_build())
    write_manifest(manifest, base_dir=get_work_dir(ctx))
    console.print(f"Version Updated from {old_version} to {manifest.version}")


version.command("set")(set_version)
version.command("patch")(patch)
version.command("minor")(minor)
version.command("major")(major)
version.command("prerelease")(prerelease)
version.command("build")(build_version)
