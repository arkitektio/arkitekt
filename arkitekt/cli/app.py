"""Typer application root for the ``arkitekt`` CLI.

This module owns the Typer root
app and its callback, which seeds the per-invocation ``ctx.obj`` state that the command
layer reads through :mod:`arkitekt.cli.vars` (console, work dir). There is no
project file to load here: each app command finds its app from its own
``module[:attr]`` target (see :mod:`arkitekt.cli.target`).

``cli/main.py`` turns this app into a plain click command via
:func:`typer.main.get_command` and mounts the command groups onto it. That keeps the
public entry point (`arkitekt.cli.main:cli`) a click object for the test suite
and ``project.scripts``.

Branding note: we use Typer's native rich rendering (``rich_markup_mode="rich"``) rather
than rich-click's ``patch_typer`` (which is version-fragile). The mark lives in the
root help text and the docs link in the epilog.
"""

import os
import sys
from typing import Any, List, Optional

import typer
from rich.console import Console
from typer.core import TyperGroup

from arkitekt.cli.docs import DOCS_BASE_URL
from arkitekt.cli.target import has_app
from arkitekt.cli.texts import MARK
from arkitekt.cli.ui import arkitekt_version
from arkitekt.cli.vars import set_console, set_work_dir

#: What stands beside the mark's three rows in the root help.
_OWN_VERSION = arkitekt_version()

#: What `--help` lists when the work dir holds an app, and when it does not. The
#: CLI is about the app in the folder: with one there, running it and its session;
#: without one, making one. Every command stays callable either way.
APP_MENU = ("run", "call", "check", "login", "logout", "status", "inspect", "gen", "plugin", "mesh", "self")
BARE_MENU = ("create", "self")

_WORK_DIR_FLAGS = ("-w", "--work-dir")


def _root_help(app_file: Optional[str]) -> str:
    """The root help text: the mark, and whether this folder holds an app."""
    here = (
        f"{os.path.basename(app_file)} in this folder"
        if app_file
        else "no app in this folder: `arkitekt create` makes one"
    )
    lines = (
        "[bold]Arkitekt[/bold]" + (f" v{_OWN_VERSION}" if _OWN_VERSION else ""),
        "[dim]the CLI for the Arkitekt Python SDK[/dim]",
        f"[dim]{here}[/dim]",
    )
    # ``\b`` keeps the rows on their own lines: Typer re-flows any other paragraph.
    return (
        "\b\n"
        + "\n".join(f"[cyan]{row:<7}[/cyan]   {line}" for row, line in zip(MARK, lines))
        + "\n\n"
        "Arkitekt is a framework for building safe and performant apps that can be "
        "centrally orchestrated and managed in workflows.\n\n"
        "This CLI works on the app in the current folder: it runs it, logs it in "
        "and out, and builds and deploys it."
    )


def _peek_work_dir(args: List[str]) -> str:
    """The work dir the root options name, read before they are parsed.

    ``--help`` is eager and exits while the options are still being processed, so
    by then ``--work-dir`` may not have been seen. What the help lists depends on
    it, whichever of the two comes first on the command line.
    """
    for index, arg in enumerate(args):
        if not arg.startswith("-"):
            break  # the subcommand: what follows are its options, not the root's
        if arg in _WORK_DIR_FLAGS and index + 1 < len(args):
            return args[index + 1]
        if arg.startswith("--work-dir="):
            return arg.split("=", 1)[1]
    return "."


class FolderGroup(TyperGroup):
    """The root group: it lists the commands that fit the work dir.

    Listing is all that changes. A command off the list is still found by name,
    and one that needs an app says so when there is none.
    """

    # The contexts are typed ``Any``: Typer hands its own vendored click's, or the
    # real click's on an older Typer, and neither is ours to name.
    def parse_args(self, ctx: Any, args: List[str]) -> List[str]:  # noqa: ANN401
        """Note the work dir, and say in the help whether it holds an app."""
        app_file = has_app(_peek_work_dir(args))
        ctx.meta[_APP_FILE] = app_file
        self.help = _root_help(app_file)
        return super().parse_args(ctx, args)

    def list_commands(self, ctx: Any) -> List[str]:  # noqa: ANN401
        """The menu for the work dir, in menu order."""
        mounted = set(super().list_commands(ctx))
        menu = APP_MENU if ctx.meta.get(_APP_FILE) else BARE_MENU
        return [name for name in menu if name in mounted]


#: Where the group keeps the app file it found, on the invocation's context.
_APP_FILE = "arkitekt.cli.app_file"

cli_app = typer.Typer(
    cls=FolderGroup,
    rich_markup_mode="rich",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=_root_help(None),
    epilog=f"📖 Learn more: [link={DOCS_BASE_URL}]{DOCS_BASE_URL}[/link]",
)


def _print_version(value: bool) -> None:
    """Eager `--version` callback: print the installed version and exit."""
    if value:
        from importlib.metadata import version

        typer.echo(version("arkitekt"))
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
    # Long flag only: `init` uses `-v` for the version it scaffolds.
    version: bool = typer.Option(
        False,
        "--version",
        callback=_print_version,
        is_eager=True,
        help="Print the arkitekt version and exit.",
    ),
) -> None:
    # Seed the per-invocation state that the command layer reads via cli.vars. This
    # runs before any (Typer or mounted-click) subcommand, so ctx.obj is populated by
    # the time get_console/get_work_dir are called downstream. The work dir goes
    # first on sys.path because that is where an app target's module is imported from.
    work_dir = os.path.abspath(work_dir)
    sys.path.insert(0, work_dir)

    ctx.obj = {}
    set_console(ctx, Console())
    set_work_dir(ctx, work_dir)

