"""What a run says in the terminal: one line each, led by a glyph of the mark.

``■`` a step starting, ``◆`` something done, ``□`` a notice, ``✕`` a failure.
The login prompt lives here, not in the CLI, so an app started with
``python app.py`` asks the same way as one started with ``arkitekt run``.
"""

import ipaddress
import os
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from rich.console import Console
from rich.markup import escape
from rich.text import Text

if TYPE_CHECKING:
    from fakts.grants.remote.authorizers.device_code import DeviceCodeChallenge, DeviceCodeHook
    from fakts.grants.remote.models import FaktsEndpoint

#: The glyph leading each kind of status line, and what a terminal that cannot
#: encode it gets instead.
STEP = ("■", "#")
DONE = ("◆", "*")
NOTICE = ("□", "-")
FAIL = ("✕", "x")


def _status(
    console: Console,
    glyph: tuple[str, str],
    style: str,
    message: str,
    detail: str | None,
) -> None:
    lead = glyph[console.options.ascii_only]
    line = f"[{style}]{lead}[/] {message}"
    if detail:
        line += f"  [dim]{detail}[/]"
    console.print(line, highlight=False)


def step(console: Console, message: str, detail: str | None = None) -> None:
    """Say that something is starting. ``message`` and ``detail`` are rich markup:
    :func:`rich.markup.escape` anything that is not yours."""
    _status(console, STEP, "cyan", message, detail)


def done(console: Console, message: str, detail: str | None = None) -> None:
    """Say that something succeeded."""
    _status(console, DONE, "green", message, detail)


def notice(console: Console, message: str, detail: str | None = None) -> None:
    """Say something that is neither a step nor an outcome."""
    _status(console, NOTICE, "yellow", message, detail)


def fail(console: Console, message: str, detail: str | None = None) -> None:
    """Say that something failed. It only prints: exiting is the caller's."""
    _status(console, FAIL, "red", message, detail)


#: ``0`` never shows the approval link as a QR code, ``1`` always does. The name
#: fakts' own prompt reads too.
QR_ENV = "FAKTS_QR"

_HALF_BLOCKS = {(False, False): " ", (True, False): "▀", (False, True): "▄", (True, True): "█"}


def force_qr() -> None:
    """Show the approval link as a QR code whatever the login looks like: what
    ``--qr`` does. Through the environment, so the prompt of this process, of
    fakts, and of any process a run starts all draw one."""
    os.environ[QR_ENV] = "1"


def _forced_qr() -> bool:
    return os.environ.get(QR_ENV, "").strip() == "1"


def _wants_qr(link: str, opened_browser: bool) -> bool:
    """A QR code is for approving on another device -- a phone, when the app runs
    over SSH, in a container or on a shared instrument PC. So not when the page
    already opened here, and not for a loopback address no phone can reach."""
    setting = os.environ.get(QR_ENV, "").strip()
    if setting in ("0", "1"):
        return setting == "1"
    if opened_browser:
        return False
    host = (urlparse(link).hostname or "").lower()
    if not host or host == "localhost" or host.endswith(".localhost"):
        return False
    try:
        return not ipaddress.ip_address(host).is_loopback
    except ValueError:
        return True


def _qr(console: Console, link: str) -> None:
    """Print ``link`` as a QR code, in half blocks: black on white whatever the
    theme (a code a dark theme inverts is one some scanners refuse), or, without
    colours, the light modules drawn on the dark background most terminals have."""
    if console.options.ascii_only and not _forced_qr():
        # Half blocks are not ASCII: drawn only when the code is asked for by name.
        return
    import segno  # only a login that is approved elsewhere draws one

    plain = console.color_system is None
    # make_qr, not make: a short link would otherwise become a Micro QR code,
    # which phone cameras do not read.
    rows = [
        [bool(module) != plain for module in row]
        for row in segno.make_qr(link, error="l").matrix_iter(border=2)
    ]
    if len(rows) % 2:
        rows.append([plain] * len(rows[0]))
    for top, bottom in zip(rows[::2], rows[1::2], strict=True):
        line = "".join(_HALF_BLOCKS[pair] for pair in zip(top, bottom, strict=True))
        console.print(
            Text.assemble("  ", (line, "" if plain else "black on white")),
            no_wrap=True,
            crop=False,
            highlight=False,
        )


def login_prompt(opened_browser: bool = True) -> "DeviceCodeHook":
    """The device-code hook that asks the user to approve the app.

    Args:
        opened_browser: Whether the approval page was opened for them. The hook
            is called after that happened and is not told, so whoever builds the
            authorizer says it here.

    Returns:
        The hook.
    """

    async def prompt(challenge: "DeviceCodeChallenge") -> None:
        console = Console()
        link, code = challenge.verification_uri_complete, challenge.user_code
        step(
            console,
            f"Log in to {escape(challenge.endpoint.name)}",
            "opened in your browser" if opened_browser else "open this link to approve the app",
        )
        console.print(f"  [link={link}]{escape(link)}[/link]", highlight=False, soft_wrap=True)
        console.print(f"  code [bold]{escape(code)}[/bold]", highlight=False)
        if _wants_qr(link, opened_browser):
            _qr(console, link)

    return prompt


async def logged_in(endpoint: "FaktsEndpoint", token: str) -> None:
    """The granted hook: say that the login went through. The token is the
    session's access token and is never shown."""
    done(Console(), f"Logged in to {escape(endpoint.name)}")


__all__ = [
    "DONE",
    "FAIL",
    "NOTICE",
    "STEP",
    "done",
    "fail",
    "force_qr",
    "logged_in",
    "login_prompt",
    "notice",
    "step",
]
