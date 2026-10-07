import asyncio
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.markup import escape

from arkitekt.app.app import App
from arkitekt.app.terminal import fail
from arkitekt.cli.commands.app.call.remote import parse_call_args, print_result
from arkitekt.cli.commands.app.run.utils import explicit_options
from arkitekt.cli.context import load_context
from arkitekt.cli.errors import cli_error
from arkitekt.cli.failures import report_failure
from arkitekt.cli.options import (
    ContextFileOption,
    ContextOption,
    HeadlessOption,
    LogLevel,
    LogLevelOption,
    ReauthOption,
    RedeemTokenOption,
    SkipCacheOption,
    TokenOption,
    UrlOption,
)
from arkitekt.cli.running import connected_local
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.utils import configure_logging
from arkitekt.cli.vars import get_console, get_work_dir
from arkitekt.constants import DEFAULT_ARKITEKT_URL

#: The connection flags a local call takes: all of a run's but ``--force``, which
#: is about a registration, and a local call registers nothing.
LOCAL_OPTIONS = ("url", "token", "redeem_token", "headless", "skip_cache", "reauth")


class UnknownActionError(LookupError):
    """The app has no action of that name."""


def require_action(app: App[Any], action: str) -> None:
    """Refuse a name the app does not offer, saying which it does."""
    offered = sorted(app.registry.implementations)
    if action not in offered:
        raise UnknownActionError(
            f"The app '{app.identifier}' has no action '{action}'. "
            + (f"It has: {', '.join(offered)}." if offered else "It has no actions.")
        )


def describe_arguments(app: App[Any], action: str) -> str:
    """The arguments ``action`` takes, as one line: ``a (INT), b (INT, optional)``."""
    ports = app.registry.implementations[action].definition.args
    described = [
        f"{port.key} ({str(getattr(port.kind, 'value', port.kind))}"
        + (", optional" if port.nullable or port.default is not None else "")
        + ")"
        for port in ports
    ]
    return ", ".join(described) or "nothing"


def require_arguments(app: App[Any], action: str, kwargs: Dict[str, Any]) -> None:
    """Refuse a call that names an argument the action lacks, or leaves a required one out.

    Raises:
        ValueError: Saying what the action takes.
    """
    ports = app.registry.implementations[action].definition.args
    known = {port.key for port in ports}
    required = {port.key for port in ports if not port.nullable and port.default is None}
    unknown = sorted(set(kwargs) - known)
    missing = sorted(required - set(kwargs))
    if not unknown and not missing:
        return
    problems = []
    if unknown:
        problems.append(f"takes no argument {', '.join(unknown)}")
    if missing:
        problems.append(f"needs {', '.join(missing)} (pass it as -a {missing[0]}=...)")
    raise ValueError(
        f"'{action}' {' and '.join(problems)}. It takes: {describe_arguments(app, action)}."
    )


async def call_locally(
    console: Console,
    app: App[Any],
    action: str,
    kwargs: Dict[str, Any],
    options: Dict[str, Any],
    offline: bool = True,
    context: Any = None,  # noqa: ANN401
) -> List[Any]:
    """Start ``app`` for itself, call ``action`` once, and return everything it yielded.

    Each result is as it travels (JSON), without the port keys a server sees: the
    one value of an action returning one, a list of an action returning several.
    """
    keys = [port.key for port in app.registry.implementations[action].definition.returns]
    results: List[Any] = []
    async with connected_local(console, app, options, offline=offline, context=context) as rt:
        async for returns in rt.aiterate_local_raw(action, kwargs):
            values = [returns.get(key) for key in keys]
            results.append(values[0] if len(values) == 1 else values or None)
    return results


def local(
    ctx: typer.Context,
    action: Annotated[
        str,
        typer.Argument(help="The action to call: the name of the function.", show_default=False),
    ],
    target: TargetArgument = DEFAULT_TARGET,
    args: Annotated[
        List[str],
        typer.Option(
            "--arg",
            "-a",
            help="An argument of the call, as key=value (the value is read as JSON when it parses).",
        ),
    ] = [],
    online: Annotated[
        bool,
        typer.Option(
            "--online",
            help="Connect the services the app uses to a deployment, with its saved session. "
            "Without it nothing is reached and nothing is logged in to.",
        ),
    ] = False,
    url: UrlOption = DEFAULT_ARKITEKT_URL,
    token: TokenOption = None,
    redeem_token: RedeemTokenOption = None,
    headless: HeadlessOption = False,
    log_level: LogLevelOption = LogLevel.ERROR,
    skip_cache: SkipCacheOption = False,
    reauth: ReauthOption = False,
    context: ContextOption = None,
    context_file: ContextFileOption = None,
) -> None:
    """Call one of this app's own actions, right here, and print what it returns.

    The app is started as a run starts it and the action goes through its ports,
    but nothing is registered and no server assigns anything: it is the quick way
    to try an action while writing it. No server is reached either: a service
    the app uses is there to be handed out, and a call through it fails. With
    --online the services are connected to a deployment, with the app's saved
    session; the connection flags are for that.
    """
    console = get_console(ctx)
    configure_logging(log_level.value)

    try:
        kwargs = parse_call_args(args or [])
    except ValueError as e:
        cli_error(str(e))

    app = load_app_or_exit(ctx, target)
    try:
        require_action(app, action)
        require_arguments(app, action, kwargs)
    except (UnknownActionError, ValueError) as e:
        cli_error(str(e))
    options = explicit_options(ctx, LOCAL_OPTIONS)
    if not online:
        # Only what was typed: an exported FAKTS_URL is for the commands that
        # connect, and must not get in the way of the one that does not.
        typed = [
            "--" + name.replace("_", "-")
            for name in options
            # By name: typer's source enum is not click's (see `explicit_options`).
            if getattr(ctx.get_parameter_source(name), "name", None) == "COMMANDLINE"
        ]
        if typed:
            cli_error(
                f"{', '.join(typed)} is about a connection, and a local call makes none without --online."
            )
    loaded = load_context(app, context, context_file, get_work_dir(ctx))

    from arkitekt_runtime.local import LocalCallError

    try:
        results = asyncio.run(
            call_locally(
                console,
                app,
                action,
                kwargs,
                options,
                offline=not online,
                context=loaded,
            )
        )
    except LocalCallError as e:
        fail(console, f"{escape(action)} failed", escape(e.error))
        raise typer.Exit(code=1) from None
    except Exception as e:
        # A failure the user can act on is one line; anything else keeps its traceback.
        if report_failure(console, e):
            raise typer.Exit(code=1) from None
        raise

    for result in results:
        print_result(console, result)
