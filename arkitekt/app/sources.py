"""Where a connection option comes from: a value, nothing, or a cascade of sources.

Every option a deployment may set from outside (``url``, ``token``, ``supervisor``, …)
takes one of three things:

- a **value**, used as it is: ``run(app, supervisor="plugin_engine")``;
- ``None``, which is *none*: nothing is sent or used, and nothing is looked up;
- a **source**: where to look, tried in order, first hit wins. ``"arg"`` is a flag on
  the command line (``--supervisor X`` or ``--supervisor=X``), ``"env"`` the
  environment variable, ``"default"`` the built-in fallback. Any in-order part of
  ``"arg-env-default"`` is a source; ``"discover"`` is all of it, and every option's
  default.

A string that is not one of those eight spellings is a value.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Sequence
from typing import Literal, TypeVar, get_args

Source = Literal[
    "discover",
    "arg",
    "env",
    "default",
    "arg-env",
    "arg-default",
    "env-default",
    "arg-env-default",
]
"""Where to look for an option, in order: ``arg``, ``env``, ``default``."""

DISCOVER: Source = "discover"
"""The command line, then the environment, then the built-in default."""

SOURCES: frozenset[str] = frozenset(get_args(Source))

T = TypeVar("T")

_TRUE = ("", "1", "true", "yes", "on")
_FALSE = ("0", "false", "no", "off")


def is_source(value: object) -> bool:
    """Whether ``value`` names where to look rather than being the value."""
    return isinstance(value, str) and value in SOURCES


def cascade(source: Source) -> tuple[str, ...]:
    """The sources a spec tries, in order: ``"discover"`` is ``("arg", "env", "default")``."""
    return ("arg", "env", "default") if source == DISCOVER else tuple(source.split("-"))


def from_argv(flag: str, argv: Sequence[str] | None = None, *, boolean: bool = False) -> str | None:
    """The value of ``--flag`` on the command line (``--flag v`` or ``--flag=v``), else None.

    A boolean flag takes no separate value (``--reauth`` is ``""``, i.e. on; ``--reauth=0``
    is off), so it never swallows the argument after it. The last occurrence wins.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    name = f"--{flag}"
    found: str | None = None
    for index, arg in enumerate(args):
        if arg == name:
            following = args[index + 1] if index + 1 < len(args) else None
            takes_next = not boolean and following is not None and not following.startswith("--")
            found = following if takes_next else ""
        elif arg.startswith(name + "="):
            found = arg[len(name) + 1 :]
    return found


def as_bool(text: str, *, what: str) -> bool:
    """A flag's or a variable's text as a boolean: present or ``1`` is on, ``0`` off."""
    value = text.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError(f"{what}={text!r} is not understood: use 1 (on) or 0 (off).")


def resolve(
    value: T | Source | None,
    *,
    flag: str,
    env: str,
    default: Callable[[], T | None],
    parse: Callable[[str], T | None],
    boolean: bool = False,
    argv: Sequence[str] | None = None,
) -> T | None:
    """The option's value: ``value`` itself, or what its source cascade finds first.

    Args:
        value: A value (returned as is), ``None`` (none), or a :data:`Source`.
        flag: The command-line flag ``arg`` reads, without the dashes.
        env: The environment variable ``env`` reads.
        default: What ``default`` gives, computed only when it is reached.
        parse: Turns a flag's or a variable's text into the value. It may raise on a
            typo: only when that source is the one consulted.
        boolean: Whether the flag is a switch (``--reauth``) rather than ``--flag value``.
        argv: The command line to read; ``sys.argv`` when not given.

    Returns:
        The value, or None when ``value`` is None or no source in the cascade has one.
    """
    if not is_source(value):
        return value  # type: ignore[return-value]  # a value, or None: none
    for source in cascade(value):  # type: ignore[arg-type]
        if source == "arg":
            text = from_argv(flag, argv, boolean=boolean)
            if text is not None:
                return parse(text)
        elif source == "env":
            text = os.environ.get(env)
            if text is not None and text.strip() != "":
                return parse(text)
        elif source == "default":
            return default()
    return None
