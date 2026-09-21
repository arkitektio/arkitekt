import asyncio

import typer

from arkitekt import runtime
from arkitekt.cli.context import load_context
from arkitekt.cli.errors import cli_error
from arkitekt.cli.options import (
    ContextFileOption,
    ContextOption,
    ForceOption,
    HeadlessOption,
    LogLevel,
    LogLevelOption,
    NoCacheOption,
    RedeemTokenOption,
    TokenOption,
    UrlOption,
)
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.ui import construct_run_panel
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
    no_cache: NoCacheOption = False,
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
    # Resolved before the run panel and the connection: an App that declares an
    # app context does not run without one, and that is a prompt-time error.
    loaded = load_context(app, context, context_file, get_work_dir(ctx))
    if loaded is not None:
        options["context"] = loaded

    console.print(construct_run_panel(app))

    try:
        # Through the module, so the runner stays replaceable (tests patch it).
        asyncio.run(runtime.arun(app, **options))
    except KeyboardInterrupt:
        pass
    except Exception:
        console.print_exception()
        cli_error("App crashed while running. See the traceback above.")
