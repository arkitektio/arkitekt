import asyncio
import json
from typing import Annotated, Any, Dict, List, Optional

import typer

from rich.console import Console

from arkitekt.app.app import App
from arkitekt.app.fakts import resolve_url
from arkitekt.cli.commands.app.run.utils import runner_options
from arkitekt.cli.errors import cli_error
from arkitekt.cli.failures import report_failure
from arkitekt.cli.options import (
    HeadlessOption,
    LogLevel,
    LogLevelOption,
    ReauthOption,
    RedeemTokenOption,
    SkipCacheOption,
    TokenOption,
    UrlOption,
)
from arkitekt.cli.running import connected
from arkitekt.cli.target import DEFAULT_TARGET, TARGET_ENVVAR, has_app, load_app_or_exit
from arkitekt.cli.ui import construct_app_banner
from arkitekt.cli.utils import configure_logging
from arkitekt.cli.vars import get_console, get_work_dir
from arkitekt.constants import DEFAULT_ARKITEKT_URL
from arkitekt.runtime import RuntimeNotInstalledError

#: The identity ``call remote`` connects as.
CLI_APP_IDENTIFIER = "arkitekt-cli"


def cli_app() -> App[None]:
    """The app every ``call remote`` connects as: rekuest, and nothing else.

    A call is made by the command line, not by the app whose action is called:
    who calls does not depend on what is called. Calling needs only an identity
    and the rekuest service; it offers nothing, so nothing is provided.

    Raises:
        RuntimeNotInstalledError: If rekuest is not installed.
    """
    try:
        from rekuest.arkitekt import rekuest_service
    except ImportError as e:
        raise RuntimeNotInstalledError(
            "Calling actions needs rekuest, which is not installed: "
            "pip install 'arkitekt[rekuest]'."
        ) from e

    return App(
        CLI_APP_IDENTIFIER,
        description="The arkitekt command line, calling actions on the server.",
        services=[rekuest_service],
    )


def parse_call_args(args: List[str]) -> Dict[str, Any]:
    """``["n=3", "name=bob"]`` -> ``{"n": 3, "name": "bob"}``.

    Values are read as JSON when they parse as JSON (numbers, booleans, lists,
    objects, quoted strings) and taken as plain strings otherwise, because the call
    sends already-serialized arguments: what is typed is what the server gets.

    Raises:
        ValueError: If an argument has no ``=``.
    """
    parsed: Dict[str, Any] = {}
    for arg in args:
        key, sep, raw = arg.partition("=")
        if not sep or not key:
            raise ValueError(f"'{arg}' is not a 'key=value' argument.")
        try:
            parsed[key] = json.loads(raw)
        except json.JSONDecodeError:
            parsed[key] = raw
    return parsed


async def call_app(
    console: Console, app: App[Any], hash: str, kwargs: Dict[str, Any], options: Dict[str, Any]
) -> Any:  # noqa: ANN401
    """Connect ``app`` (without providing it), find the action by hash, and call it.

    The call goes through the run's rekuest client, so only actions available on
    the connected server can be called.
    """
    from rekuest.client.client import Rekuest

    async with connected(console, app, options) as rt:
        rekuest = rt.require(Rekuest)
        action = await rekuest.afind(hash=hash)
        return await rekuest.acall_raw(kwargs=kwargs, action=action)


def _looks_like_a_hash(value: str) -> bool:
    """Whether ``value`` could be a definition hash: 64 hexadecimal characters."""
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def hash_of(app: App[Any], action: str) -> Optional[str]:
    """The hash of the action ``app`` declares under ``action``, if it declares one.

    The hash is of the definition (name, ports, ...), so it is the same on the
    server: it finds the action there, whichever agent provides it.
    """
    from arkitekt_spec import definition_hash

    implementation = app.registry.implementations.get(action)
    return definition_hash(implementation.definition) if implementation else None


def remote(
    ctx: typer.Context,
    action: Annotated[
        str,
        typer.Argument(
            help=(
                "The action to call: the name of one of this app's actions, or the "
                "hash of any action on the server (`arkitekt inspect implementations` "
                "lists both)."
            ),
            show_default=False,
        ),
    ],
    target: Annotated[
        Optional[str],
        typer.Argument(
            envvar=TARGET_ENVVAR,
            help=(
                "The app whose action is named, as 'module[:attr]' (like uvicorn). "
                "Defaults to the app in this folder. It only turns the name into a "
                f"hash: the call is always made as '{CLI_APP_IDENTIFIER}'."
            ),
            show_default=False,
        ),
    ] = None,
    url: UrlOption = DEFAULT_ARKITEKT_URL,
    token: TokenOption = None,
    redeem_token: RedeemTokenOption = None,
    headless: HeadlessOption = False,
    log_level: LogLevelOption = LogLevel.ERROR,
    skip_cache: SkipCacheOption = False,
    reauth: ReauthOption = False,
    args: Annotated[
        List[str],
        typer.Option(
            "--arg",
            "-a",
            help="An argument of the call, as key=value (the value is read as JSON when it parses).",
        ),
    ] = [],
):
    """Call an action on the connected server and print its output.

    The server assigns the call to whichever agent provides the action: for one of
    this app's own, that is this app only while it runs (`arkitekt run dev`), and
    it may as well be a copy of it running elsewhere. To call the code in front of
    you, use `arkitekt call local`.

    An action of this app is named; any other is given by its hash. The app is
    only read to turn the name into a hash: the call is always made as
    'arkitekt-cli', which logs in once per server, whatever is called.
    """

    console = get_console(ctx)
    configure_logging(log_level.value)

    try:
        kwargs = parse_call_args(args or [])
    except ValueError as e:
        cli_error(str(e))

    # The app only names the action. One that was asked for must load; the one
    # this folder happens to hold is used if it is there.
    named: Optional[App[Any]] = None
    if target is not None:
        named = load_app_or_exit(ctx, target)
    elif has_app(get_work_dir(ctx)):
        named = load_app_or_exit(ctx, DEFAULT_TARGET)

    hash = (hash_of(named, action) if named is not None else None) or action
    if hash == action and not _looks_like_a_hash(action):
        # Neither one of the app's actions nor a hash: a typo, most likely.
        offered = sorted(named.registry.implementations) if named is not None else []
        cli_error(
            f"'{action}' is neither an action of "
            + (f"the app '{named.identifier}' " if named is not None else "an app in this folder ")
            + "nor the hash of one on the server."
            + (f" The app has: {', '.join(offered)}." if offered else "")
        )
    try:
        app = cli_app()
    except RuntimeNotInstalledError as e:
        cli_error(str(e))
    options = runner_options(ctx)
    console.print(construct_app_banner(app, resolve_url(options.get("url"))))

    try:
        result = asyncio.run(call_app(console, app, hash, kwargs, options))
    except LookupError as e:
        cli_error(str(e))
    except Exception as e:
        # A failure the user can act on is one line; anything else keeps its traceback.
        if report_failure(console, e):
            raise typer.Exit(code=1) from None
        raise

    print_result(console, result)


def print_result(console: Console, result: Any) -> None:  # noqa: ANN401
    """Print what a call returned: as JSON when it is JSON, as it is otherwise."""
    if _is_json(result):
        console.print_json(data=result)
    else:
        console.print(result)


def _is_json(value: Any) -> bool:  # noqa: ANN401
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False
    return True
