"""The failures of a run a user can do something about, each as one line.

A run that fails in one of these ways needs no traceback: it needs to be told
what happened and what to do next. Anything else is a bug and keeps its traceback.
"""


from collections.abc import Callable

from rich.console import Console
from rich.markup import escape

from arkitekt.app.terminal import fail
from arkitekt.cli.ui import command_hint

#: What to say for each, and what to do about it. Matched by class name, over
#: the exception's whole ancestry: the agent's classes are rekuest's, which is an
#: optional extra, and fakts' are deep in its grants.
#: A hint is said as it is, or made when it is said: one that names a command
#: depends on the project it is about.
Hint = str | Callable[[str | None], str] | None

_KNOWN: dict[str, tuple[str, Hint]] = {
    "AgentIsAlreadyBusy": (
        "Another instance of this app is already connected",
        "pass --force to take over",
    ),
    "AgentWasKicked": ("Another instance of this app took over its connection", None),
    "AgentWasBlocked": ("The server blocked this app's agent", None),
    "UserDeniedError": ("The login was declined", None),
    "DeviceCodeExpiredError": ("The login was not approved in time", "run it again"),
    "DeviceCodeTimeoutError": ("The login was not approved in time", "run it again"),
    "NeedsReauthenticationError": (
        "The session is no longer valid",
        lambda work_dir: f"log in again with `{command_hint('login --reauth', work_dir)}`",
    ),
    "DiscoveryError": ("Could not reach the server", "check --url"),
}


def explain(error: BaseException, work_dir: str | None = None) -> tuple[str, str | None] | None:
    """What to say about ``error``, and the hint to give, if it is a known failure."""
    names = [cls.__name__ for cls in type(error).__mro__]
    if "RuntimeNotInstalledError" in names:
        # It already says what to install.
        return (str(error), None)
    if "DefiniteConnectionFail" in names:
        # One class for every way the transport gives up; the message says which.
        text = str(error).lower()
        if "kicked" in text:
            return ("Another instance of this app took over its connection", None)
        if "retries" in text or "flapping" in text:
            return ("Lost the connection to the server and could not get it back", None)
        return None
    for name in names:
        if name in _KNOWN:
            message, hint = _KNOWN[name]
            # A hint that names a command is made now: how it is started depends on the project.
            return (message, hint(work_dir) if callable(hint) else hint)
    return None


def report_failure(console: Console, error: BaseException, work_dir: str | None = None) -> bool:
    """Print the line for ``error`` if it is a known failure. Returns whether it was."""
    known = explain(error, work_dir)
    if known is None:
        return False
    message, hint = known
    fail(console, escape(message), hint)
    return True


__all__ = ["explain", "report_failure"]
