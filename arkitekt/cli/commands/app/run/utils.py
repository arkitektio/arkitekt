from typing import Any
from collections.abc import Iterable

import typer

from arkitekt.app.fakts import forced_mesh
from fakts.models import AliasPolicy

__all__ = [
    "CONNECTION_OPTIONS",
    "explicit_options",
    "runner_options",
]


#: The command-line flags that change how a run connects. Only those the user
#: actually passed reach the runner. ``--log-level`` is not one of them: it
#: configures this process, which the command does before it runs anything.
CONNECTION_OPTIONS = (
    "url",
    "token",
    "mandate_key",
    "force",
    "headless",
    "skip_cache",
    "reauth",
    "device_id",
    "supervisor",
)


#: Where a value came from when it was not passed. Compared by name: Typer vendors
#: its own click, so its ``ParameterSource`` members are not ``click``'s, and an
#: identity check against ``click.core.ParameterSource.DEFAULT`` never matches --
#: which would count every default as passed.
_NOT_PASSED = {"DEFAULT", "DEFAULT_MAP"}


def explicit_options(ctx: typer.Context, names: Iterable[str]) -> dict[str, Any]:
    """The values of the options the user actually passed, leaving defaults out.

    A flag's default must not override the runner's own resolution: an unpassed
    ``--url`` leaves the url to ``FAKTS_URL`` and the runtime's default, instead
    of pinning it to whatever default this command happens to show.
    """
    explicit: dict[str, Any] = {}
    for name in names:
        source = ctx.get_parameter_source(name)
        if source is not None and source.name not in _NOT_PASSED:
            explicit[name] = ctx.params[name]
    return explicit


def runner_options(ctx: typer.Context) -> dict[str, Any]:
    """The keyword arguments a run command hands to :func:`arkitekt.arun`: the
    explicitly passed connection flags. ``--force-mesh`` goes as the ``mesh``
    it stands for, ``--prefer-reach`` / ``--exclude-reach`` as the ``alias_policy``."""
    options = explicit_options(ctx, CONNECTION_OPTIONS)
    if explicit_options(ctx, ("force_mesh",)).get("force_mesh"):
        options["mesh"] = forced_mesh()
    reaches = explicit_options(ctx, ("prefer_reach", "exclude_reach"))
    if reaches:
        # The flags passed replace what the environment says of the same thing.
        # Validated: an unknown reach is refused here, not ignored.
        options["alias_policy"] = AliasPolicy(
            **{**AliasPolicy.from_env().model_dump(), **{key: list(value) for key, value in reaches.items() if value}}
        )
    return options
