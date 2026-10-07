import asyncio

import typer

from arkitekt.app.fakts import resolve_url
from arkitekt.cli.context import load_context
from arkitekt.cli.errors import cli_error
from arkitekt.cli.failures import report_failure
from arkitekt.cli.options import (
    ContextFileOption,
    ContextOption,
    ForceMeshOption,
    ForceOption,
    HeadlessOption,
    LogLevel,
    LogLevelOption,
    ReauthOption,
    SkipCacheOption,
    RedeemTokenOption,
    TokenOption,
    UrlOption,
)
from arkitekt.cli.running import arun_app, interruptible
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.ui import construct_app_banner, notice
from arkitekt.cli.utils import configure_logging
from arkitekt.cli.vars import get_console, get_work_dir
from arkitekt.constants import DEFAULT_ARKITEKT_URL

from .utils import runner_options


def prod(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    url: UrlOption = DEFAULT_ARKITEKT_URL,
    token: TokenOption = None,
    redeem_token: RedeemTokenOption = None,
    force: ForceOption = False,
    headless: HeadlessOption = False,
    log_level: LogLevelOption = LogLevel.ERROR,
    skip_cache: SkipCacheOption = False,
    reauth: ReauthOption = False,
    force_mesh: ForceMeshOption = False,
    context: ContextOption = None,
    context_file: ContextFileOption = None,
) -> None:
    """Runs the app in production mode

    Runs the App the target module declares (``app = App(...)``). The App decides
    what it is; the connection flags you pass decide only how this run connects,
    and are handed to the runner rather than written onto the App.
    """

    console = get_console(ctx)
    configure_logging(log_level.value)
    app = load_app_or_exit(ctx, target)
    options = runner_options(ctx)
    # Resolved before the banner and the connection: an App that declares an
    # app context does not run without one, and that is a prompt-time error.
    loaded = load_context(app, context, context_file, get_work_dir(ctx))

    console.print(construct_app_banner(app, resolve_url(options.get("url"))))

    async def until_stopped() -> None:
        try:
            await arun_app(console, app, options, context=loaded)
        except asyncio.CancelledError:
            # Said before the teardown that follows, which may take a moment.
            notice(console, "Stopping", "Ctrl+C again to force")
            raise

    try:
        with interruptible(console):
            asyncio.run(until_stopped())
    except Exception as e:
        # A failure the user can act on is one line; anything else is a crash.
        if report_failure(console, e):
            raise typer.Exit(code=1) from None
        console.print_exception()
        cli_error("App crashed while running. See the traceback above.")
