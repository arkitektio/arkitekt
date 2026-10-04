"""What a run says in the terminal: one line each, led by a glyph of the mark.

``■`` a step starting, ``◆`` something done, ``□`` a notice, ``✕`` a failure.
The login prompt lives here, not in the CLI, so an app started with
``python app.py`` asks the same way as one started with ``arkitekt run``.
"""

from typing import TYPE_CHECKING, Optional, Tuple

from rich.console import Console
from rich.markup import escape

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
    glyph: Tuple[str, str],
    style: str,
    message: str,
    detail: Optional[str],
) -> None:
    lead = glyph[console.options.ascii_only]
    line = f"[{style}]{lead}[/] {message}"
    if detail:
        line += f"  [dim]{detail}[/]"
    console.print(line, highlight=False)


def step(console: Console, message: str, detail: Optional[str] = None) -> None:
    """Say that something is starting. ``message`` and ``detail`` are rich markup:
    :func:`rich.markup.escape` anything that is not yours."""
    _status(console, STEP, "cyan", message, detail)


def done(console: Console, message: str, detail: Optional[str] = None) -> None:
    """Say that something succeeded."""
    _status(console, DONE, "green", message, detail)


def notice(console: Console, message: str, detail: Optional[str] = None) -> None:
    """Say something that is neither a step nor an outcome."""
    _status(console, NOTICE, "yellow", message, detail)


def fail(console: Console, message: str, detail: Optional[str] = None) -> None:
    """Say that something failed. It only prints: exiting is the caller's."""
    _status(console, FAIL, "red", message, detail)


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
    "logged_in",
    "login_prompt",
    "notice",
    "step",
]
