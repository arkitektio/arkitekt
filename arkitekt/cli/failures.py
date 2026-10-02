"""The failures of a run a user can do something about, each as one line.

A run that fails in one of these ways needs no traceback: it needs to be told
what happened and what to do next. Anything else is a bug and keeps its traceback.
"""

from typing import Optional, Tuple

from rich.console import Console
from rich.markup import escape

from arkitekt.app.terminal import fail

#: What to say for each, and what to do about it. Matched by class name, over
#: the exception's whole ancestry: the agent's classes are rekuest's, which is an
#: optional extra, and fakts' are deep in its grants.
_KNOWN = {
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
        "log in again with `arkitekt login --reauth`",
    ),
    "DiscoveryError": ("Could not reach the server", "check --url"),
}


def explain(error: BaseException) -> Optional[Tuple[str, Optional[str]]]:
    """What to say about ``error``, and the hint to give, if it is a known failure."""
    names = [cls.__name__ for cls in type(error).__mro__]
    if "RuntimeNotInstalledError" in names:
        # It already says what to install.
        return (str(error), None)
    if "DefiniteConnectionFail" in names:
        # One class for every way the transport gives up; the message says which.
        text = str(error).lower()
        if "kicked" in text:
            return _KNOWN["AgentWasKicked"]
        if "retries" in text or "flapping" in text:
            return ("Lost the connection to the server and could not get it back", None)
        return None
    for name in names:
        if name in _KNOWN:
            return _KNOWN[name]
    return None


def report_failure(console: Console, error: BaseException) -> bool:
    """Print the line for ``error`` if it is a known failure. Returns whether it was."""
    known = explain(error)
    if known is None:
        return False
    message, hint = known
    fail(console, escape(message), hint)
    return True


__all__ = ["explain", "report_failure"]
