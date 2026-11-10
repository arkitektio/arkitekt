"""``arkitekt plugin badge``: the "Open in Arkitekt" badge for the app's README.

The badge installs the app's published package: a click opens the reader's
Orkestrator on "Install an app" for ``ghcr.io/<owner>/<repo>``, which is where
the release workflow (``arkitekt plugin ci github``) publishes it. It names an
*intent* of Orkestrator's, ``/do/v1/repo.install?source=oci:<reference>``,
not one of its pages, so a badge keeps working however the app changes
(``core/links/LINKS.md`` in orkestrator). Orkestrator builds the same string and
pins it in its own test; ``tests/cli/test_badge.py`` pins it here. Change both
or neither.

Which package is not known before the code is on GitHub, so the README carries
a marked place for the badge (written by ``arkitekt create``) and the release
workflow fills it in on its first run, from the repository it runs in.
"""

import os
import re
from urllib.parse import quote, urlencode

import typer

from arkitekt.cli.errors import cli_error
from arkitekt.cli.ui import done, escape, notice
from arkitekt.cli.vars import get_console, get_work_dir

from .release import _source

#: The image every app's badge shows.
BADGE_IMAGE_URL = "https://arkitekt.live/img/badge/open-in-arkitekt.svg"

#: Hands the path to whichever Orkestrator is installed, and shows a landing page when none is.
DEEPLINK_BASE = "https://arkitekt.live/deeplink"

#: The intent, and the highest version of it this writes.
INTENT = "repo.install"
INTENT_VERSION = 1

#: Where the badge goes in a README. Only what is between them is ever rewritten.
START = "<!-- arkitekt:badge -->"
END = "<!-- /arkitekt:badge -->"

#: What stands in the badge's place until the repository is known: invisible on GitHub.
PLACEHOLDER = "<!-- The release workflow puts the 'Open in Arkitekt' badge here on its first run. -->"

_SEGMENT = re.compile(r"^[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*$")


def normalize_reference(raw: str) -> str:
    """The OCI repository ``raw`` names, as Kabinet reads one, or a ``ValueError``.

    The repository alone (``ghcr.io/owner/app``), never a tag or a digest, and
    lowercased: a repository path is lowercase, a GitHub owner's name need not be.
    Mirrors kabinet's ``parse_reference`` and orkestrator's ``parseOciReference``.
    """
    reference = raw.strip().lower().removeprefix("oci://").removeprefix("https://").rstrip("/")
    if not reference or len(reference) > 255 or not re.fullmatch(r"[a-z0-9._:/-]+", reference):
        raise ValueError(f"'{raw}' is not a package: name the repository alone, e.g. ghcr.io/owner/app.")
    head, _, rest = reference.partition("/")
    is_host = "." in head or ":" in head or head == "localhost"
    path = rest.split("/") if rest and is_host else reference.split("/")
    if not all(_SEGMENT.fullmatch(segment) for segment in path):
        raise ValueError(f"'{raw}' is not a package: name the repository alone, without a tag or a digest.")
    return reference


def install_path(reference: str) -> str:
    """The Orkestrator path of the install intent for one package."""
    return f"/do/v{INTENT_VERSION}/{INTENT}?" + urlencode({"source": f"oci:{reference}"})


#: What ``encodeURIComponent`` leaves as it is, besides letters, digits and ``-_.~``
#: (which ``quote`` always keeps): the link must be Orkestrator's, byte for byte.
_URI_COMPONENT_SAFE = "!*'()"


def install_link(reference: str) -> str:
    """The link a badge points at: the intent's path as the deeplink page's one parameter."""
    return f"{DEEPLINK_BASE}?orkestrator={quote(install_path(reference), safe=_URI_COMPONENT_SAFE)}"


def install_badge(reference: str) -> str:
    """The README markdown: the generic badge image over this package's install link."""
    return f"[![Open in Arkitekt]({BADGE_IMAGE_URL})]({install_link(reference)})"


_GITHUB_REMOTE = re.compile(r"^(?:[a-z+]+://)?(?:[^@/]+@)?github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", re.IGNORECASE)


def package_for_remote(url: str | None) -> str | None:
    """The package the release workflow publishes for a checkout of ``url``:
    ``ghcr.io/<owner>/<repo>`` for a GitHub remote, ``None`` for anything else."""
    match = _GITHUB_REMOTE.match(url.strip()) if url else None
    return f"ghcr.io/{match.group(1)}/{match.group(2)}".lower() if match else None


def _block(content: str) -> str:
    return f"{START}\n{content}\n{END}"


def write_badge(readme: str, content: str, insert: bool = True) -> bool:
    """Put ``content`` (a badge, or the placeholder) between the README's markers.

    Args:
        readme: The README's path.
        content: What goes between the markers.
        insert: Add the markers when the README has none: under its first heading,
            else at its top (and make the README when there is none). Without it a
            README whose author removed the badge is left alone.

    Returns:
        Whether the README changed.
    """
    existing = ""
    if os.path.exists(readme):
        with open(readme, encoding="utf-8") as file:
            existing = file.read()

    start, end = existing.find(START), existing.find(END)
    if start != -1 and end > start:
        updated = existing[:start] + _block(content) + existing[end + len(END) :]
    elif not insert:
        return False
    else:
        lines = existing.splitlines(keepends=True)
        heading = next((index for index, line in enumerate(lines) if line.startswith("# ")), None)
        if heading is None:
            updated = _block(content) + "\n" + ("\n" + existing if existing else "")
        else:
            before = "".join(lines[: heading + 1])
            if not before.endswith("\n"):
                before += "\n"
            updated = before + "\n" + _block(content) + "\n" + "".join(lines[heading + 1 :])

    if updated == existing:
        return False
    with open(readme, "w", encoding="utf-8") as file:
        file.write(updated)
    return True


def badge(
    ctx: typer.Context,
    repository: str | None = typer.Option(
        None,
        "--repository",
        help="The package the badge installs, e.g. ghcr.io/owner/app. Default: the one the release "
        "workflow publishes for this checkout's GitHub remote.",
    ),
    write: bool = typer.Option(False, "--write", help="Put it in the README, adding its place there if needed."),
    update: bool = typer.Option(
        False, "--update", help="Put it in the README only where its place already is (what the workflow runs)."
    ),
    readme: str = typer.Option("README.md", "--readme", help="The README, relative to the app."),
) -> None:
    """Print the 'Open in Arkitekt' README badge that installs this app, or write it into the README"""
    work_dir = get_work_dir(ctx)
    raw = repository or package_for_remote(_source(work_dir))
    if raw is None:
        cli_error(
            "This checkout has no GitHub remote, so which package to install is not known. "
            "Pass --repository ghcr.io/owner/app, or push it to GitHub first."
        )
    try:
        reference = normalize_reference(raw)
    except ValueError as error:
        cli_error(str(error))

    markdown = install_badge(reference)
    if not (write or update):
        typer.echo(markdown)
        return

    console = get_console(ctx)
    if write_badge(os.path.join(work_dir, readme), markdown, insert=write):
        done(console, f"{escape(readme)} has the badge for [bold]{escape(reference)}[/bold]")
    elif update and START not in _read(os.path.join(work_dir, readme)):
        notice(console, f"{escape(readme)} has no place for the badge", "left as it is; add it with --write")
    else:
        done(console, f"{escape(readme)} already has the badge for [bold]{escape(reference)}[/bold]")


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as file:
            return file.read()
    except OSError:
        return ""
