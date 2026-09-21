from typing import Any, Dict, Iterable

import typer

__all__ = [
    "CONNECTION_OPTIONS",
    "explicit_options",
    "runner_options",
]


#: The command-line flags that change how a run connects. Only those the user
#: actually passed reach the runner. ``--log-level`` is not one of them: it
#: configures this process, which the command does before it runs anything.
CONNECTION_OPTIONS = ("url", "token", "redeem_token", "force", "headless", "no_cache")


#: Where a value came from when it was not passed. Compared by name: Typer vendors
#: its own click, so its ``ParameterSource`` members are not ``click``'s, and an
#: identity check against ``click.core.ParameterSource.DEFAULT`` never matches --
#: which would count every default as passed.
_NOT_PASSED = {"DEFAULT", "DEFAULT_MAP"}


def explicit_options(ctx: typer.Context, names: Iterable[str]) -> Dict[str, Any]:
    """The values of the options the user actually passed, leaving defaults out.

    A flag's default must not override the runner's own resolution: an unpassed
    ``--url`` leaves the url to ``FAKTS_URL`` and the runtime's default, instead
    of pinning it to whatever default this command happens to show.
    """
    explicit: Dict[str, Any] = {}
    for name in names:
        source = ctx.get_parameter_source(name)
        if source is not None and source.name not in _NOT_PASSED:
            explicit[name] = ctx.params[name]
    return explicit


def runner_options(ctx: typer.Context, *, reauth: bool = False) -> Dict[str, Any]:
    """The keyword arguments a run command hands to :func:`arkitekt.arun`.

    The explicitly passed connection flags. ``reauth`` skips the fakts cache, so
    a fresh login runs.
    """
    options = explicit_options(ctx, CONNECTION_OPTIONS)
    if reauth:
        options["no_cache"] = True
    return options
