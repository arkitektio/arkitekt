"""Shell completion of values: an app's actions, its flavours, its services.

Each completer is handed the context of the command line typed so far, before any
callback has run, so it finds ``--work-dir`` on the root's parameters itself.
Completing must never print or fail: whatever goes wrong completes nothing.
Importing the app to name its actions is done offline, the way ``check`` does it,
so a completion never connects or runs anything.
"""

import contextlib
import io
import os
import sys
from typing import Any

import typer

#: Where `plugin flavour add` keeps the flavours, under the work dir.
FLAVOURS_DIR = (".arkitekt", "flavours")


def _work_dir(ctx: Any) -> str:  # noqa: ANN401
    """The ``--work-dir`` typed so far, else the current directory."""
    root = ctx.find_root() if ctx is not None else None
    work_dir = (getattr(root, "params", None) or {}).get("work_dir")
    return os.path.abspath(work_dir or ".")


def _target(ctx: Any) -> str:  # noqa: ANN401
    """The app target typed so far, else the one a command defaults to."""
    typed = (getattr(ctx, "params", None) or {}).get("target")
    return typed or os.environ.get("ARKITEKT_APP") or "app"


def _quietly(load: Any) -> Any:  # noqa: ANN401
    """Run ``load`` with nothing reaching the terminal, and ``None`` on any failure."""
    sink = io.StringIO()
    try:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            return load()
    except BaseException:  # a completion must not even exit
        return None


def _app(ctx: Any) -> Any:  # noqa: ANN401
    from arkitekt.cli.offline import offline
    from arkitekt.cli.target import load_target

    def load() -> Any:  # noqa: ANN401
        work_dir = _work_dir(ctx)
        # The root callback puts the work dir first on sys.path for a run; a
        # completion is answered before any callback, so it does that itself.
        sys.path.insert(0, work_dir)
        try:
            with offline():
                return load_target(_target(ctx), work_dir)[0]
        finally:
            sys.path.remove(work_dir)

    return _quietly(load)


def _starting_with(names: Any, incomplete: str) -> list[str]:  # noqa: ANN401
    return sorted(name for name in names if name.startswith(incomplete))


def complete_actions(ctx: typer.Context, incomplete: str) -> list[str]:
    """The names of the app's actions."""
    app = _app(ctx)
    return [] if app is None else _starting_with(app.registry.implementations, incomplete)


def complete_flavours(ctx: typer.Context, incomplete: str) -> list[str]:
    """The flavours in the work dir's ``.arkitekt/flavours``."""
    folder = os.path.join(_work_dir(ctx), *FLAVOURS_DIR)
    try:
        names = [name for name in os.listdir(folder) if os.path.isdir(os.path.join(folder, name))]
    except OSError:
        return []
    return _starting_with(names, incomplete)


def complete_services(ctx: typer.Context, incomplete: str) -> list[str]:
    """The services the app declares."""
    app = _app(ctx)
    if app is None:
        return []
    from arkitekt.cli.commands.app.inspect.utils import run_snapshot_or_exit

    snapshot = _quietly(lambda: run_snapshot_or_exit(app))
    return [] if snapshot is None else _starting_with(snapshot.services, incomplete)


__all__ = ["complete_actions", "complete_flavours", "complete_services"]
