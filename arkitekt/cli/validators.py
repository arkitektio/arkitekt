"""Typer callbacks that check an option against what is actually available.

The choices are compiled at call time -- templates and dockerfiles are files on
disk (:mod:`arkitekt.cli.constants`), so they cannot be a static ``Enum``. Every
one of these callbacks was the same three lines, so they share one factory.
"""

from typing import Callable, List, Optional

import typer

from arkitekt.cli.constants import compile_dockerfiles, compile_scopes, compile_templates


def _one_of(what: Callable[[], List[str]]) -> Callable[[Optional[str]], Optional[str]]:
    """Make a callback rejecting anything ``what()`` does not list.

    Args:
        what: Compiles the valid choices, at call time.

    Returns:
        A typer callback that passes ``None`` through and raises
        :class:`typer.BadParameter` for an unlisted value.
    """

    def validate(value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        choices = what()
        if value not in choices:
            raise typer.BadParameter(f"'{value}' is not one of {', '.join(choices)}.")
        return value

    return validate


validate_template = _one_of(compile_templates)
"""Check ``--template`` against the app templates in ``cli/templates``."""

validate_dockerfile = _one_of(compile_dockerfiles)
"""Check ``--template`` against the dockerfiles in ``cli/dockerfiles``."""


def validate_scopes(value: List[str]) -> List[str]:
    """Check every ``--scope`` against the known scopes.

    Args:
        value: The scopes as passed.

    Returns:
        The scopes, unchanged.

    Raises:
        typer.BadParameter: On the first scope that is not a known one.
    """
    valid = compile_scopes()
    for scope in value:
        if scope not in valid:
            raise typer.BadParameter(f"'{scope}' is not one of {', '.join(valid)}.")
    return value


__all__ = ["validate_template", "validate_dockerfile", "validate_scopes"]
