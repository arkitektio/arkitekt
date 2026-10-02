"""How the CLI looks: the mark, and the status lines drawn from its glyphs.

Nothing here draws a box. A run opens with the mark beside what it is about
(:func:`construct_app_banner`), and everything after it is a single line led by
one of the mark's own glyphs: ``■`` a step starting, ``◆`` something done,
``□`` a notice, ``✕`` a failure. Those lines are :mod:`arkitekt.app.terminal`'s,
shared with a run started outside the CLI, and re-exported here.
"""

import os
from importlib.metadata import PackageNotFoundError, version
from itertools import zip_longest
from typing import Any, Callable, Dict, MutableSet, Optional, Tuple

from rich.console import Console, ConsoleOptions, Group, RenderableType, RenderResult
from rich.markup import escape
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

from arkitekt.app import App
from arkitekt.app.terminal import FAIL, STEP, done, fail, notice, step

from .texts import ASCII_MARK, MARK

#: What stands between an app and its author.
SEPARATOR = ("·", "-")

#: The gap between the mark (or a label) and the text beside it.
GUTTER = 3


def arkitekt_version() -> Optional[str]:
    """The installed arkitekt version, or None when it runs from a source tree."""
    try:
        return version("arkitekt")
    except PackageNotFoundError:
        return None


class Adaptive:
    """A renderable built once the console is known, from whether it is ASCII only.

    Rich swaps a panel's border for ASCII by itself; a glyph inside a text it
    writes as given, and a stream that cannot encode it raises.
    """

    def __init__(self, build: Callable[[bool], RenderableType]) -> None:
        self.build = build

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        yield self.build(options.ascii_only)


class Banner:
    """The mark, with up to three lines of text beside it."""

    def __init__(self, *lines: RenderableType) -> None:
        self.lines = lines

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        grid = Table.grid(padding=(0, GUTTER, 0, 0))
        grid.add_column(style="cyan", no_wrap=True)
        grid.add_column()
        mark = ASCII_MARK if options.ascii_only else MARK
        for row, line in zip_longest(mark, self.lines, fillvalue=""):
            grid.add_row(row, line)
        yield grid


def construct_banner(*lines: RenderableType) -> Banner:
    """The mark beside ``lines``, the first of them led by the Arkitekt version."""
    own = arkitekt_version()
    title = Text("Arkitekt", style="bold")
    if own:
        title.append(f" v{own}", style="not bold")
    return Banner(title, *lines)


def _details(rows: Dict[str, str]) -> Table:
    grid = Table.grid(padding=(0, GUTTER, 0, 0))
    grid.add_column(style="dim", no_wrap=True)
    grid.add_column()
    for label, value in rows.items():
        grid.add_row(label, Text(value))
    return grid


def construct_app_banner(
    app: App[Any], url: str, connection: str = "connecting to"
) -> Adaptive:
    """What a run prints first: the app, where it connects, and what it declares.

    It displays the app's identity and what it declares, read off the App itself:
    the App is the only place the identity lives. ``url`` is the resolved fakts
    url (see :func:`arkitekt.app.fakts.resolve_url`), not the flag.

    Parameters
    ----------
    app : App
        The app to construct the banner for
    url : str
        The fakts server the run connects to
    connection : str
        What the command does with that server, said before its url

    Returns
    -------
    Adaptive
        A rich renderable
    """
    server = Text(f"{connection} ", style="dim")
    server.append(url, style="not dim")

    # Rendered from the declaration, not a snapshot: a declaration the run will
    # reject is the run's error to report, not the banner's.
    rows: Dict[str, str] = {}
    if app.services:
        rows["services"] = ", ".join(app.services)

    # An app offering actions is served by rekuest's provider without listing the
    # rekuest service, so the definitions are shown whenever there are any.
    actions = [
        template.interface or template.definition.name
        for template in app.registry.get_implementations()
    ]
    if actions:
        rows["actions"] = ", ".join(actions)

    def build(ascii_only: bool) -> Group:
        identity = Text(f"{app.identifier} {app.version}")
        if app.author:
            identity.append(f" {SEPARATOR[ascii_only]} {app.author}", style="dim")
        banner = construct_banner(identity, server)
        if not rows:
            return Group(banner, "")
        return Group(banner, "", _details(rows), "")

    return Adaptive(build)


def construct_section(title: str, body: RenderableType) -> Group:
    """A titled block: what a boxed panel around ``body`` used to be."""
    return Group(Text(title, style="bold"), Padding(body, (0, 0, 0, 2)))


def construct_changes_group(changes: MutableSet[Tuple[Any, str]]) -> Adaptive:
    """Construct the status lines for the detected changes

    They are displayed if the app has detected changes before
    running the app. This can be caused by a change in the code or
    a change in the environment (e.g. a new package was installed)"""
    paths = sorted({os.path.normpath(path) for _, path in changes})
    return Adaptive(
        lambda ascii_only: Group(
            Text.assemble((STEP[ascii_only], "cyan"), " changed"),
            Padding(Text("\n".join(paths), style="dim"), (0, 0, 0, 2)),
        )
    )


def construct_leaking_group(variables: Dict[str, Any]) -> Adaptive:
    """Construct the report for the leaking variables

    It is displayed if the app has leaking variables
    and is therefore considered to be not safe to run
    as an Arkitekt plugin

    Parameters
    ----------
    variables : Dict[str, Any]
        The leaking variables

    Returns
    -------
    Adaptive
        The rich renderable
    """
    explanation = Text(
        "Your app is leaking variables. Leaking variables can cause memory leaks "
        "and other issues. Please make sure you are not defining variables in the "
        "global scope (outside of functions). If you want to define constants "
        "please make them all UPPERCASE.",
        style="dim",
    )
    leaking = _details({key: str(value) for key, value in variables.items()})
    return Adaptive(
        lambda ascii_only: Group(
            Text.assemble((FAIL[ascii_only], "red"), " Detected leaking variables"),
            Padding(explanation, (0, 0, 1, 2)),
            Padding(leaking, (0, 0, 0, 2)),
        )
    )


__all__ = [
    "Adaptive",
    "Banner",
    "GUTTER",
    "arkitekt_version",
    "construct_app_banner",
    "construct_banner",
    "construct_changes_group",
    "construct_leaking_group",
    "construct_section",
    "done",
    "escape",
    "fail",
    "notice",
    "step",
]
