"""Typer application root for the ``arkitekt-next`` CLI.

This module owns the Typer root
app and its callback, which seeds the per-invocation ``ctx.obj`` state that the command
layer reads through :mod:`arkitekt_next.cli.vars` (console, work dir, manifest).

``cli/main.py`` turns this app into a plain click command via
:func:`typer.main.get_command` and mounts the command groups onto it. That keeps the
public entry point (`arkitekt_next.cli.main:cli`) a click object for the test suite
and ``project.scripts``.

Branding note: we use Typer's native rich rendering (``rich_markup_mode="rich"``) rather
than rich-click's ``patch_typer`` (which is version-fragile). The ASCII logo lives in the
root help text and the docs link in the epilog.
"""

import os
import sys

import typer
from rich.console import Console

from arkitekt_next.cli.docs import DOCS_BASE_URL
from arkitekt_next.cli.io import load_manifest
from arkitekt_next.cli.texts import LOGO
from arkitekt_next.cli.vars import set_console, set_manifest, set_work_dir
from arkitekt_next.utils import create_arkitekt_next_folder

#: Root commands that operate on a scaffolded app project (a manifest inside the
#: `.arkitekt_next` folder). They need the folder to exist and the manifest loaded
#: into context; `init` is the command that creates that project, so it is excluded.
APP_PROJECT_COMMANDS = {"run", "gen", "manifest", "inspect", "call"}

_ROOT_HELP = (
    f"[cyan]{LOGO}[/cyan]\n\n"
    "ArkitektNext is a framework for building safe and performant apps that can be "
    "centrally orchestrated and managed in workflows.\n\n"
    "This is the CLI for the ArkitektNext Python SDK. It lets you create and deploy "
    "ArkitektNext Apps from your Python code and run them locally for testing and "
    "development."
)

cli_app = typer.Typer(
    rich_markup_mode="rich",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=_ROOT_HELP,
    epilog=f"📖 Learn more: [link={DOCS_BASE_URL}]{DOCS_BASE_URL}[/link]",
)


def _print_version(value: bool) -> None:
    """Eager `--version` callback: print the installed version and exit."""
    if value:
        from importlib.metadata import version

        typer.echo(version("arkitekt-next"))
        raise typer.Exit()


@cli_app.callback()
def main(
    ctx: typer.Context,
    work_dir: str = typer.Option(
        ".",
        "--work-dir",
        "-w",
        is_eager=True,
        help="Working directory for the app. Defaults to the current directory.",
    ),
    # Long flag only: `-v` is reserved for the app-version override on the run
    # commands (see cli/options.py::VersionOption).
    version: bool = typer.Option(
        False,
        "--version",
        callback=_print_version,
        is_eager=True,
        help="Print the arkitekt-next version and exit.",
    ),
) -> None:
    # Seed the per-invocation state that the command layer reads via cli.vars. This
    # runs before any (Typer or mounted-click) subcommand, so ctx.obj is populated by
    # the time get_console/get_work_dir are called downstream.
    work_dir = os.path.abspath(work_dir)
    sys.path.insert(0, work_dir)

    ctx.obj = {}
    set_console(ctx, Console())
    set_work_dir(ctx, work_dir)

    if ctx.invoked_subcommand in APP_PROJECT_COMMANDS:
        create_arkitekt_next_folder(base_dir=work_dir)

        manifest = load_manifest(base_dir=work_dir)
        if manifest:
            set_manifest(ctx, manifest)
