import rich_click as click
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Group
from rich.console import Console
from semver import parse as parse_semver
from arkitekt.cli.vars import get_console, get_manifest
from arkitekt.cli.io import write_manifest


@click.group()
@click.pass_context
def version(ctx):
    """Updates the version of the arkitekt app

    Arkitekt manifests versioning follow [link=https://semver.org]semver[/link] and are used to version the app.

    """


@version.command("set")
@click.argument("VERSION", type=str, required=False)
@click.pass_context
def set_version(ctx, version):
    manifest = get_manifest(ctx)
    console = get_console(ctx)
    old_version = manifest.version

    if not version:
        try:
            potential_new_version = parse_semver(old_version, loaded=True).bump_patch()
        except Exception:
            potential_new_version = None

        new_version = click.prompt(
            "Please provide a new version", default=potential_new_version, type=str
        )
        version = parse_semver(new_version)
        version = new_version

    manifest.version = version
    write_manifest(manifest)
    get_console().print(f"Version Updated from {old_version} to {version}")


@version.command()
@click.pass_context
def patch(ctx):
    "Patches the version of the arkitekt app"
    manifest = get_manifest(ctx)
    console = get_console(ctx)
    old_version = manifest.version
    manifest.version = parse_semver(old_version).bump_patch()
    write_manifest(manifest)
    console.print(f"Version Updated from {old_version} to {manifest.version}")


@version.command()
@click.pass_context
def minor(ctx):
    "Patches the version of the arkitekt app"
    manifest = get_manifest(ctx)
    console = get_console(ctx)
    old_version = manifest.version
    manifest.version = parse_semver(old_version).bump_minor()
    write_manifest(manifest)
    console.print(f"Version Updated from {old_version} to {manifest.version}")


@version.command()
@click.pass_context
def major(ctx):
    "Patches the version of the arkitekt app"
    manifest = get_manifest(ctx)
    console = get_console(ctx)
    old_version = manifest.version
    manifest.version = parse_semver(old_version).bump_major()
    write_manifest(manifest)
    console.print(f"Version Updated from {old_version} to {manifest.version}")


@version.command()
@click.pass_context
def prerelease(ctx):
    "Patches the version of the arkitekt app"
    manifest = get_manifest(ctx)
    console = get_console(ctx)
    old_version = manifest.version
    manifest.version = parse_semver(old_version).bump_prerelease()
    write_manifest(manifest)
    console.print(f"Version Updated from {old_version} to {manifest.version}")


@version.command("build")
@click.pass_context
def bump_build(ctx):
    "Patches the version of the arkitekt app"
    manifest = get_manifest(ctx)
    console = get_console(ctx)
    old_version = manifest.version
    manifest.version = parse_semver(old_version).bump_build()
    write_manifest(manifest)
    console.print(f"Version Updated from {old_version} to {manifest.version}")
