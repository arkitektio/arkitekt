"""The plugin command group, mounted only when kabinet is installed.

`arkitekt plugin ...` builds, validates and publishes plugins through kabinet,
which is an extra: ``pip install "arkitekt[kabinet]"``. Without it the group is
a stub that says so, rather than a traceback at import time.
"""

from collections.abc import Callable

import typer

KABINET_HINT = (
    "The plugin commands need kabinet, which is not installed. "
    "Install it with: pip install 'arkitekt[kabinet]'"
)


def _load_plugin_group() -> typer.Typer:
    from .main import plugin

    return plugin


def plugin_group(load: Callable[[], typer.Typer] = _load_plugin_group) -> typer.Typer:
    """The plugin group, or a stub explaining the missing extra.

    Args:
        load: What imports the real group; raises ``ImportError`` without kabinet.
    """
    try:
        return load()
    except ImportError:
        stub = typer.Typer(
            help="Build, validate and publish plugins (needs the kabinet extra).",
            invoke_without_command=True,
        )

        @stub.callback()
        def _needs_kabinet(ctx: typer.Context) -> None:
            typer.echo(KABINET_HINT, err=True)
            raise typer.Exit(code=1)

        return stub


__all__ = ["KABINET_HINT", "plugin_group"]
