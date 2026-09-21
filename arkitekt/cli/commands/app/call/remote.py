import asyncio
import json
from typing import Annotated, Any, Dict, List, Optional

import typer

from arkitekt import runtime
from arkitekt.app.app import App
from arkitekt.cli.commands.app.run.utils import runner_options
from arkitekt.cli.errors import cli_error
from arkitekt.cli.options import (
    HeadlessOption,
    LogLevel,
    LogLevelOption,
    NoCacheOption,
    TokenOption,
    UrlOption,
)
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.ui import construct_run_panel
from arkitekt.cli.utils import configure_logging
from arkitekt.cli.vars import get_console
from arkitekt.constants import DEFAULT_ARKITEKT_URL


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


async def call_app(app: App, hash: str, kwargs: Dict[str, Any], options: Dict[str, Any]) -> Any:  # noqa: ANN401
    """Connect ``app`` (without providing it), find the action by hash, and call it.

    The call goes through the run's rekuest client, so only actions available on
    the connected server can be called -- this app's own functions are not served.
    """
    from rekuest.client.client import Rekuest

    # Through the module, so the connection stays replaceable (tests patch it).
    async with runtime.connect(app, **options) as rt:
        rekuest = rt.get(Rekuest)
        if rekuest is None:
            raise LookupError(
                f"The app '{app.identifier}' does not use rekuest, so it cannot call "
                "actions. Declare an action on it, or `app.service(Rekuest)`."
            )
        action = await rekuest.afind(hash=hash)
        return await rekuest.acall_raw(kwargs=kwargs, action=action)


def remote(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    url: UrlOption = DEFAULT_ARKITEKT_URL,
    token: TokenOption = None,
    headless: HeadlessOption = False,
    log_level: LogLevelOption = LogLevel.ERROR,
    no_cache: NoCacheOption = False,
    args: Annotated[
        List[str],
        typer.Option(
            "--arg",
            "-a",
            help="An argument of the call, as key=value (the value is read as JSON when it parses).",
        ),
    ] = [],
    hash: Annotated[
        Optional[str],
        typer.Option(
            "--hash",
            help="The hash of the action to run",
        ),
    ] = None,
):
    """Call an action on the connected server and print its output.

    This is useful for debugging and testing. In this mode the app itself will not
    be run, so local actions cannot be called. Only actions that are available on your
    arkitekt server can be called. The app is used for its identity and services:
    it is what connects.
    """

    console = get_console(ctx)
    configure_logging(log_level.value)

    if hash is None:
        cli_error("Pass the --hash of the action to call.")
    try:
        kwargs = parse_call_args(args or [])
    except ValueError as e:
        cli_error(str(e))

    app = load_app_or_exit(ctx, target)
    console.print(construct_run_panel(app))

    try:
        result = asyncio.run(call_app(app, hash, kwargs, runner_options(ctx)))
    except LookupError as e:
        cli_error(str(e))

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
