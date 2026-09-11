"""CLI error/abort helpers.

Typer 0.26 vendors its own copy of ``click``, so a real ``click.ClickException``
raised inside a command is no longer caught by Typer's error handler (it would leak
as a traceback). :func:`cli_error` / :func:`confirm_or_abort` reproduce click's clean
"Error: ..." / abort behaviour using Typer's own primitives.

Migration mapping:
- ``raise click.ClickException(msg)``  ->  ``cli_error(msg)``  (cli_error raises)
- ``click.confirm(q, abort=True)``     ->  ``confirm_or_abort(q)``
- ``click.confirm(q)``                 ->  ``typer.confirm(q)``
"""

from typing import NoReturn

import typer


class ValidationError(Exception):
    """Raised when a validation error occurs."""

    pass


def cli_error(message: str) -> NoReturn:
    """Print a clean error and exit non-zero (the Typer equivalent of ClickException).

    Renders ``Error: <message>`` in red on stderr and raises ``typer.Exit(1)``. Because
    it raises, call it directly (no ``raise``): ``cli_error("...")``.
    """
    typer.secho(f"Error: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


def confirm_or_abort(question: str) -> None:
    """Prompt for confirmation and abort (exit non-zero) if declined.

    Equivalent to click's ``confirm(question, abort=True)``.
    """
    if not typer.confirm(question):
        raise typer.Abort()
