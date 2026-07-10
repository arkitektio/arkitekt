"""Guard interactive prompts so the CLI never blocks on stdin in a non-TTY.

Several commands drop into interactive prompts (``click.prompt`` /
``click.confirm`` / ``inquirer.prompt``) to gather configuration. When stdin is
not a terminal -- CI, a pipe, ``nohup`` -- those calls block forever with no way
to abort. ``require_interactive`` is the single guard to call before any such
prompt: on a non-TTY it raises a clean :class:`click.ClickException` that names
the non-interactive escape hatch instead of hanging.

This mirrors the ``sys.stdin.isatty()`` guard already used in
``arkitekt_next.cli.commands.hub.connect``.
"""

import sys

from arkitekt_next.cli.errors import cli_error


def is_interactive() -> bool:
    """True when stdin is a real terminal we can prompt on."""
    try:
        return sys.stdin.isatty()
    except (ValueError, AttributeError):  # stdin closed / replaced
        return False


def require_interactive(purpose: str, *, hint: str) -> None:
    """Abort with guidance if there is no TTY to run ``purpose`` interactively.

    ``purpose`` describes what needs prompting (e.g. ``"the configuration
    wizard"``); ``hint`` names the non-interactive alternative (e.g. ``"pass
    --template to skip it"``). No-op when stdin is a terminal.
    """
    if is_interactive():
        return
    cli_error(
        f"{purpose} needs an interactive terminal, but stdin is not a TTY "
        f"(are you running in CI or through a pipe?). {hint}"
    )
