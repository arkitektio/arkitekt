import contextlib
import sys
from collections.abc import Callable, Iterator
from typing import Any
import json

from rich.console import Console
import logging
import os


def emit_machine_readable(kind: str, data: Any) -> None:
    """Print ``data`` as JSON wrapped in ``--START_<KIND>--``/``--END_<KIND>--``.

    The sentinels let consumers (e.g. ``plugin build``'s in-container inspection)
    extract the payload from otherwise noisy stdout. Every ``--machine-readable``
    command emits through this helper so the framing stays uniform.
    """
    print(f"--START_{kind}--" + json.dumps(data) + f"--END_{kind}--")


def build_relative_dir(*paths):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *paths)


def configure_logging(log_level: str) -> None:
    """Configure root logging at ``log_level``, prettily when rich is installed.

    The one place logging is configured: a *command* owns the process, so it may.
    A run (:class:`arkitekt.Runtime`) never does, since a library that
    reconfigures logging behind the caller's back is a nuisance.

    Args:
        log_level: A level name, e.g. ``"DEBUG"``.
    """
    try:
        from rich.logging import RichHandler

        logging.basicConfig(level=log_level, handlers=[RichHandler()])
    except ImportError:
        logging.basicConfig(level=log_level)


@contextlib.contextmanager
def json_stdout(enabled: bool) -> Iterator[Callable[[Any], None]]:
    """Keep stdout for one JSON document, when ``enabled``.

    Inside, whatever else would reach stdout (an app's own prints while it is
    imported) goes to stderr. Yields the function that prints the document to
    the real stdout; it does nothing when not ``enabled``.
    """
    stdout = sys.stdout

    def emit(data: Any) -> None:  # noqa: ANN401
        if enabled:
            stdout.write(json.dumps(data, indent=2, default=str) + "\n")
            stdout.flush()

    if not enabled:
        yield emit
        return
    with contextlib.redirect_stdout(sys.stderr):
        yield emit


def human_console(console: Console, as_json: bool) -> Console:
    """The console to say things on: stderr when stdout is kept for JSON."""
    return Console(stderr=True) if as_json else console
