"""Guard interactive prompts so the CLI never blocks on stdin in a non-TTY.

Several commands drop into interactive prompts (``click.prompt`` /
``click.confirm``) to gather configuration. When stdin is not a terminal -- CI, a
pipe, ``nohup`` -- those calls block forever with no way to abort.
``require_tty`` is the single guard to call before any such prompt: on a non-TTY
it calls :func:`~arkitekt.cli.errors.cli_error`, which names the non-interactive
escape hatch instead of hanging. (It does not raise ``click.ClickException`` --
that is the very thing ``cli_error`` exists to replace under Typer's vendored
click.)

Named for the TTY, not for "interactive": :func:`arkitekt.interactive` means
something else entirely -- a notebook session, where sync calls run inside a
running event loop -- and the two used to read as the same word.
"""

import sys

from arkitekt.cli.errors import cli_error


def is_tty() -> bool:
    """True when stdin is a real terminal we can prompt on."""
    try:
        return sys.stdin.isatty()
    except (ValueError, AttributeError):  # stdin closed / replaced
        return False


def require_tty(purpose: str, *, hint: str) -> None:
    """Abort with guidance if there is no TTY to run ``purpose`` interactively.

    ``purpose`` describes what needs prompting (e.g. ``"the configuration
    wizard"``); ``hint`` names the non-interactive alternative (e.g. ``"pass
    --template to skip it"``). No-op when stdin is a terminal.
    """
    if is_tty():
        return
    cli_error(
        f"{purpose} needs an interactive terminal, but stdin is not a TTY "
        f"(are you running in CI or through a pipe?). {hint}"
    )
