from functools import partial
from importlib import reload
from types import ModuleType
import asyncio
from pathlib import Path

from watchfiles import awatch, Change
from rich.console import Console
from watchfiles.filters import PythonFilter
import os
import sys
import inspect
from typing import Annotated, Any, Iterable, List, Optional, Set, Tuple
import typer
from arkitekt.app.fakts import resolve_url
from arkitekt.cli.context import load_context
from arkitekt.cli.errors import cli_error
from arkitekt.cli.failures import report_failure
from arkitekt.cli.running import arun_app
from arkitekt.cli.ui import (
    construct_app_banner,
    construct_changes_group,
    done,
    escape,
    fail,
    notice,
)
from arkitekt.cli.commands.app.run.utils import runner_options
from arkitekt.cli.options import (
    ContextFileOption,
    ContextOption,
    LogLevel,
    UrlOption,
    TokenOption,
    RedeemTokenOption,
    ForceOption,
    HeadlessOption,
    LogLevelOption,
    ReauthOption,
    SkipCacheOption,
)
from arkitekt.cli.target import (
    DEFAULT_TARGET,
    Target,
    TargetArgument,
    TargetError,
    import_target,
    parse_target,
    require_app,
)
from arkitekt.constants import DEFAULT_ARKITEKT_URL
from arkitekt.cli.utils import configure_logging
from arkitekt.cli.vars import get_console, get_work_dir


class EntrypointFilter(PythonFilter):
    """Checks if the entrypoint is changed"""

    def __init__(self, entrypoint_real_path: str, *args, **kwargs) -> None:
        """A filter that checks if the entrypoint is changed

        Parameters
        ----------
        entrypoint_real_path : str
            The entrypoint to check
        """
        super().__init__(*args, **kwargs)
        self.entrypoint_real_path = os.path.normpath(entrypoint_real_path)

    def __call__(self, change: Change, path: str) -> bool:
        """Checks if any of the python filters are changed
        _description_
                Parameters
                ----------
                change : Change
                    The change type
                path : str
                    The causing path

                Returns
                -------
                bool
                    Should we reload?
        """
        x = super().__call__(change, path)
        if not x:
            return False

        return os.path.normpath(os.path.realpath(path)) == self.entrypoint_real_path


class DeepFilter(PythonFilter):
    """Checks if any of the python filters are changed"""

    def __call__(self, change: Change, path: str) -> bool:
        """Checks if any of the python filters are changed

        Parameters
        ----------
        change : Change
            The change type
        path : str
            The causing path

        Returns
        -------
        bool
            Should we reload?
        """
        return super().__call__(change, path)


def modules_to_reload(
    changed: Iterable[str], entrypoint_module: str, deep: bool
) -> List[str]:
    """The modules to reload for a change, in the order to reload them.

    The entrypoint always comes last, and always comes: it is what declares the
    app, and only re-running it declares a new one from the changed code.
    Reloading only its dependencies would hand back the old App, still holding
    the functions registered from the old code. In deep mode the changed modules
    come first, so the entrypoint sees them.
    """
    dependencies = sorted(set(changed) - {entrypoint_module}) if deep else []
    return [*dependencies, entrypoint_module]


def reload_modules(modules: Iterable[str]) -> None:
    """Reload ``modules`` in order."""
    for module in modules:
        reload(sys.modules[module])


def check_deeps(changes: Set[Tuple[Change, str]]) -> Set[str]:
    """Checks if any of the changes
    are happening in a module that is installed
    and returns the modules that should be reloaded



    Parameters
    ----------
    changes : Set[ Tuple[Change, str] ]
        The changes to check

    Returns
    -------
    Set[str]
        A set of modules that should be reloaded
    """
    normalized = [os.path.normpath(file) for modified, file in changes]

    reloadable_modules = set()

    for key, v in sys.modules.items():
        try:
            filepath = inspect.getfile(v)
        except OSError:
            continue
        except TypeError:
            continue

        for i in normalized:
            if filepath.startswith(i):
                reloadable_modules.add(key)

    return reloadable_modules


def callback(console: Console, future: asyncio.Task[None]):
    if future.cancelled():
        return
    else:
        has_exception = future.exception()

        if not has_exception:
            done(console, "App finished running")
        else:
            # A failure the user can act on is one line; anything else is a crash.
            if report_failure(console, has_exception):
                return
            try:
                raise has_exception
            except Exception:
                console.print_exception()
                fail(console, "Error running App")


def _start(
    console: Console,
    module: ModuleType,
    target: Target,
    options: dict[str, Any],
    what: str,
    *,
    context: Optional[str] = None,
    context_file: Optional[Path] = None,
    work_dir: str = ".",
) -> Optional[asyncio.Task[None]]:
    """Find the module's (new) App and start running it, or report why it cannot run.

    The App is looked up again on every start: a reload re-declares it, and the
    old object still holds the functions of the old code. So is its app context:
    a ``--context module:attr`` is re-imported and a ``--context-file`` re-validated
    against the reloaded class.
    """
    try:
        app = require_app(module, target.attribute)
        console.print(construct_app_banner(app, resolve_url(options.get("url"))))
        loaded = load_context(app, context, context_file, work_dir)
        run = asyncio.create_task(arun_app(console, app, options, context=loaded))
        run.add_done_callback(partial(callback, console))
        return run
    except Exception:
        console.print_exception()
        fail(console, f"Error starting {what} App")
        return None


async def _stop(console: Console, run: Optional[asyncio.Task[None]]) -> None:
    if run is None or run.done():
        return
    run.cancel()
    notice(console, "Cancelling latest version")
    try:
        await run
    except asyncio.CancelledError:
        pass


def _intro(console: Console, target: Target, deep: bool) -> None:
    watching = (
        "all your installed packages"
        if deep
        else f"{escape(os.path.basename(target.file))} (--deep watches installed packages too)"
    )
    notice(console, "Dev mode", f"reloads on change, watching {watching}")


async def run_dev(
    console: Console,
    target: Target,
    work_dir: str,
    options: dict[str, Any] | None = None,
    deep: bool = False,
    context: Optional[str] = None,
    context_file: Optional[Path] = None,
):
    """Run the target's app, and run it again whenever its code changes.

    ``options`` are the connection flags for the runner: they go to every run,
    never onto the App. ``context``/``context_file`` are the app-context flags,
    resolved anew on every start.
    """
    options = options or {}

    _intro(console, target, deep)

    module: Optional[ModuleType]
    try:
        module = import_target(target)
    except Exception:
        console.print_exception()
        fail(console, f"Error while importing your app, please fix {escape(target.file)} and save")
        module = None

    current_run = (
        _start(
            console,
            module,
            target,
            options,
            "initial",
            context=context,
            context_file=context_file,
            work_dir=work_dir,
        )
        if module
        else None
    )

    async for changes in awatch(
        work_dir,
        watch_filter=EntrypointFilter(target.file) if not deep else DeepFilter(),
        debounce=2000,
        step=500,
    ):
        changed: Set[str] = set()
        if deep:
            changed = check_deeps(changes)
            if not changed:
                continue

        console.print(construct_changes_group(changes))
        await _stop(console, current_run)
        current_run = None

        try:
            with console.status("Reloading module..."):
                if module is None:
                    module = import_target(target)
                else:
                    reload_modules(modules_to_reload(changed, target.module, deep))
                    module = sys.modules[target.module]
        except Exception:
            console.print_exception()
            fail(console, "Reload unsuccessful, please fix your app and save")
            continue

        current_run = _start(
            console,
            module,
            target,
            options,
            "reloaded",
            context=context,
            context_file=context_file,
            work_dir=work_dir,
        )


def dev(
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
    deep: Annotated[
        bool,
        typer.Option(
            "--deep",
            help="Also watch your installed packages, and reload the ones that change",
        ),
    ] = False,
    context: ContextOption = None,
    context_file: ContextFileOption = None,
) -> None:
    """Runs the app in dev mode (with hot reloading)

    Running the app in dev mode will automatically reload the app when changes are detected.
    This is useful for development and debugging. Each reload re-imports the target
    module and runs the App it declares then.
    """

    console = get_console(ctx)
    configure_logging(log_level.value)
    work_dir = get_work_dir(ctx)
    try:
        parsed = parse_target(target, work_dir)
    except TargetError as e:
        cli_error(str(e))

    try:
        asyncio.run(
            run_dev(
                console,
                parsed,
                work_dir,
                options=runner_options(ctx),
                deep=deep,
                context=context,
                context_file=context_file,
            )
        )
    except KeyboardInterrupt:
        pass
