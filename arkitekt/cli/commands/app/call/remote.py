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
from arkitekt.cli.target import TARGET_ENVVAR, load_app_or_exit
from arkitekt.cli.ui import construct_app_banner
from arkitekt.cli.utils import configure_logging
from arkitekt.cli.vars import get_console
from arkitekt.constants import DEFAULT_ARKITEKT_URL
from arkitekt.runtime import RuntimeNotInstalledError

#: The identity ``call remote`` connects as when no app is given.
CLI_APP_IDENTIFIER = "arkitekt-cli"


def cli_app() -> App[None]:
    """The app ``call remote`` connects as when no app is given: rekuest, and nothing else.

    Calling an action needs only an identity and the rekuest service; it offers
    nothing, so nothing is provided.

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
    the connected server can be called -- this app's own functions are not served.
    """
    from rekuest.client.client import Rekuest

    async with connected(console, app, options) as rt:
        rekuest = rt.get(Rekuest)
        if rekuest is None:
            raise LookupError(
                f"The app '{app.identifier}' does not use the rekuest service, so it "
                "cannot call actions. Add it (`App(..., services=[rekuest_service])`, "
                "from rekuest.arkitekt), or leave out the app argument to call as "
                f"'{CLI_APP_IDENTIFIER}'."
            )
        action = await rekuest.afind(hash=hash)
        return await rekuest.acall_raw(kwargs=kwargs, action=action)


def remote(
    ctx: typer.Context,
    target: Annotated[
        Optional[str],
        typer.Argument(
            envvar=TARGET_ENVVAR,
            help=(
                "The app to call as, as 'module[:attr]' (like uvicorn). It must use the "
                f"rekuest service. Leave it out to call as '{CLI_APP_IDENTIFIER}'."
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
    hash: Annotated[
        Optional[str],
        typer.Option(
            "--hash",
            help="The hash of the action to run",
        ),
    ] = None,
):
    """Call an action on the connected server and print its output.

    This is useful for debugging and testing. Nothing is provided, so local actions
    cannot be called: only actions available on your arkitekt server. Without an app
    argument the call is made as the 'arkitekt-cli' app; with one, as that app, which
    is then used only for its identity and services.
    """

    console = get_console(ctx)
    configure_logging(log_level.value)

    if hash is None:
        cli_error("Pass the --hash of the action to call.")
    try:
        kwargs = parse_call_args(args or [])
    except ValueError as e:
        cli_error(str(e))

    if target is None:
        try:
            app = cli_app()
        except RuntimeNotInstalledError as e:
            cli_error(str(e))
    else:
        app = load_app_or_exit(ctx, target)
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
