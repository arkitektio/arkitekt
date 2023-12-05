import contextvars
from rich.console import Console
import rich_click as click
from .types import Manifest
from typing import Dict, Any


current_console = contextvars.ContextVar("current_console")
current_manifest = contextvars.ContextVar("current_manifest")
current_builds = contextvars.ContextVar("current_builds")


def get_console() -> Console:
    try:
        return current_console.get()
    except LookupError:
        raise click.ClickException(
            "No Current Console. Probably you are not running this command from the CLI."
        )


def set_console(console):
    current_console.set(console)


def get_manifest() -> Manifest:
    """Get the current manifest or raise an exception."""
    try:
        return current_manifest.get()
    except LookupError:
        raise click.ClickException(
            "No manifest found. You need to run the `arkitekt init` command first."
        )


def set_manifest(manifest):
    current_manifest.set(manifest)


def get_builds() -> Dict[str, Any]:
    """Get the current builds or raise an exception."""
    try:
        return current_builds.get()
    except LookupError:
        raise click.ClickException(
            "No builds found. You need to run the `arkitekt build` command first."
        )


def set_builds(builds):
    current_builds.set(builds)
