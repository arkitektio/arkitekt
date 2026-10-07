from functools import partial
import sysconfig
from types import ModuleType
import asyncio
from pathlib import Path

from watchfiles import awatch
from rich.console import Console
from watchfiles.filters import PythonFilter
import os
import sys
from typing import Annotated, Any, Iterable, List, Optional, Set
import typer
from arkitekt.app.fakts import resolve_url
from arkitekt.cli.context import load_context
from arkitekt.cli.errors import cli_error
from arkitekt.cli.failures import report_failure
from arkitekt.cli.running import arun_app, interruptible
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
    ForceMeshOption,
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
    describe_import_failure,
    import_target,
    parse_target,
    require_app,
)
from arkitekt.app.app import App
from arkitekt.runtime import _provider_for
from arkitekt.constants import DEFAULT_ARKITEKT_URL
from arkitekt.cli.utils import configure_logging
from arkitekt.cli.vars import get_console, get_work_dir


#: A directory that holds an environment, not the project: its code is not the user's.
_ENVIRONMENT_DIRS = {".venv", "venv", "site-packages", "node_modules", "__pycache__"}

#: How long the watcher waits for a save to settle before it reloads, and the
#: longest it keeps collecting a burst of saves, in milliseconds. An editor writes
#: a file in several steps and a formatter rewrites it after; shorter than this
#: reloads in between.
SETTLE_MS = 100
BURST_MS = 1000


class Candidate:
    """An app that was loaded and checked, and is ready to run."""

    def __init__(self, module: ModuleType, app: App[Any], context: Any) -> None:  # noqa: ANN401
        self.module = module
        self.app = app
        self.context = context


def _under(path: str, root: str) -> bool:
    root = os.path.join(os.path.realpath(root), "")
    return os.path.realpath(path).startswith(root)


def _is_environment(path: str) -> bool:
    return bool(_ENVIRONMENT_DIRS & set(os.path.realpath(path).split(os.sep)))


def _file_of(module: ModuleType) -> Optional[str]:
    return getattr(module, "__file__", None)


def project_modules(work_dir: str, baseline: Iterable[str] = ()) -> List[str]:
    """The loaded modules that are the project's own code.

    Under the work dir, outside any environment, and not loaded before the app
    was (``baseline``): a work dir that also holds the SDK the CLI runs on, or
    scripts the app never imports, has none of that reloaded.
    """
    before = set(baseline)
    found = []
    for name, module in list(sys.modules.items()):
        file = _file_of(module) if module is not None else None
        if name in before or not file:
            continue
        if _under(file, work_dir) and not _is_environment(file):
            found.append(name)
    return found


def development_modules(work_dir: str, baseline: Iterable[str] = ()) -> List[str]:
    """The loaded modules of packages installed for development, which ``--deep`` follows.

    A package installed the usual way is a copy in ``site-packages`` that nobody
    edits. One installed editable (or linked in) is a checkout the user works on
    beside the app: outside the project, outside any environment, and not the
    standard library. Only what the app brought in counts (not in ``baseline``):
    the SDK the CLI itself runs on is never reloaded under it.
    """
    before = set(baseline)
    standard = os.path.realpath(sysconfig.get_paths()["stdlib"])
    found = []
    for name, module in list(sys.modules.items()):
        file = _file_of(module) if module is not None else None
        if name in before or not file or not file.endswith(".py"):
            continue
        if _under(file, work_dir) or _is_environment(file) or _under(file, standard):
            continue
        found.append(name)
    return found


def development_roots(work_dir: str, baseline: Iterable[str] = ()) -> List[str]:
    """The directories (or single files) the development packages live in, to watch."""
    roots: Set[str] = set()
    for name in development_modules(work_dir, baseline):
        if "." in name:
            continue
        real = os.path.realpath(sys.modules[name].__file__ or "")
        roots.add(os.path.dirname(real) if os.path.basename(real) == "__init__.py" else real)
    return sorted(roots)


def files_of(modules: Iterable[str]) -> Set[str]:
    """The source files of loaded ``modules``, as real paths."""
    files = set()
    for name in modules:
        module = sys.modules.get(name)
        file = _file_of(module) if module is not None else None
        if file:
            files.add(os.path.realpath(file))
    return files


def concerns(changes: Iterable[Any], files: Optional[Set[str]]) -> bool:
    """Whether a burst of changes touches the app.

    ``files`` is what the running app was loaded from; a change elsewhere in the
    folder (another script, a test) is not its business. ``None`` means the app
    did not load, so nothing says yet which files it is made of: any change may
    be the fix.
    """
    if files is None:
        return True
    return any(os.path.realpath(path) in files for _, path in changes)


def import_fresh(target: Target, stale: Iterable[str]) -> ModuleType:
    """Import the target again from the files as they are now, or leave everything as it was.

    The ``stale`` modules are taken out of ``sys.modules`` and the target is
    imported, which runs each of them anew as the import reaches it: into new
    module objects, so the code that is running keeps the ones it has. If the
    import fails they are all put back, and nothing has changed.

    Dropping every module the app loaded, not only the changed file, is what makes
    a change in a helper reach the modules that imported it.

    Raises:
        Exception: Whatever importing the user's code raises.
    """
    names = {*stale, target.module}
    saved = {name: sys.modules.pop(name) for name in names if name in sys.modules}
    try:
        return import_target(target)
    except BaseException:
        for name in names:
            sys.modules.pop(name, None)
        sys.modules.update(saved)
        raise


def load_candidate(
    target: Target,
    stale: Iterable[str],
    context: Optional[str] = None,
    context_file: Optional[Path] = None,
    work_dir: str = ".",
) -> Candidate:
    """Load the app from the files as they are now and check that a run would take it.

    Everything that can be wrong with the code is found here, before the app that
    is running is touched: the import, the App in it, what it declares (as a run
    validates it before connecting) and its app context. The App is looked up
    anew every time: a reload re-declares it, and the old object still holds the
    functions of the old code. So is a ``--context module:attr``, re-imported, and
    a ``--context-file``, re-validated against the reloaded class.

    Raises:
        Exception: Whatever is wrong. ``sys.modules`` is then as it was.
    """
    stale = list(stale)
    saved = {name: sys.modules[name] for name in {*stale, target.module} if name in sys.modules}
    module = import_fresh(target, stale)
    try:
        app = require_app(module, target.attribute)
        app.snapshot(provider=_provider_for(app, required=False))
        return Candidate(module, app, load_context(app, context, context_file, work_dir))
    except BaseException:
        for name in {*stale, target.module}:
            sys.modules.pop(name, None)
        sys.modules.update(saved)
        raise


def report_broken(console: Console, error: BaseException, target: Target, work_dir: str) -> None:
    """Say what is wrong with the code, where the user can fix it."""
    console.print(escape(describe_import_failure(error, target.module, work_dir)), highlight=False)


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
    candidate: Candidate,
    options: dict[str, Any],
) -> asyncio.Task[None]:
    """Start running a loaded app, reporting on its connection and its tasks."""
    console.print(construct_app_banner(candidate.app, resolve_url(options.get("url"))))
    run = asyncio.create_task(
        arun_app(console, candidate.app, options, context=candidate.context, tasks=True)
    )
    run.add_done_callback(partial(callback, console))
    return run


async def _stop(console: Console, run: Optional[asyncio.Task[None]]) -> None:
    if run is None or run.done():
        return
    run.cancel()
    try:
        await run
    except asyncio.CancelledError:
        pass


def _intro(console: Console, deep: bool) -> None:
    watching = (
        "the app, what it imports from this folder and from packages installed for development"
        if deep
        else "the app and what it imports from this folder (--deep: also from packages installed for development)"
    )
    notice(console, "Dev mode", f"reloads on change, watching {watching}")


def _running(run: Optional[asyncio.Task[None]]) -> bool:
    return run is not None and not run.done()


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

    A change is loaded and checked first, beside the app that is running. Only
    code that a run would take replaces it: a save that does not import, or
    declares something invalid, is reported and the last working version keeps
    running until the next save.

    ``options`` are the connection flags for the runner: they go to every run,
    never onto the App. ``context``/``context_file`` are the app-context flags,
    resolved anew on every start.
    """
    options = options or {}

    _intro(console, deep)

    # What was loaded before the app is the CLI and the SDK it runs on. Only what
    # the app brings in after this is the app's to reload.
    baseline = frozenset(sys.modules)

    def loaded() -> List[str]:
        mine = project_modules(work_dir, baseline)
        return [*mine, *development_modules(work_dir, baseline)] if deep else mine

    def tracked() -> Set[str]:
        return files_of(loaded()) | {os.path.realpath(target.file)}

    current_run: Optional[asyncio.Task[None]] = None
    # The files the app that loaded last is made of; None while nothing loads.
    files: Optional[Set[str]] = None
    try:
        current_run = _start(
            console, load_candidate(target, [], context, context_file, work_dir), options
        )
        files = tracked()
    except Exception as e:
        report_broken(console, e, target, work_dir)
        fail(console, "The app does not load", f"fix {escape(os.path.basename(target.file))} and save")

    # What --deep follows is read off what the app imported, so it is known once
    # the app has loaded: a first import that failed leaves only the project.
    roots = development_roots(work_dir, baseline) if deep else []

    try:
        async for changes in awatch(
            work_dir, *roots, watch_filter=PythonFilter(), debounce=BURST_MS, step=SETTLE_MS
        ):
            if not concerns(changes, files):
                continue
            console.print(construct_changes_group(changes))
            try:
                with console.status("Loading the change..."):
                    candidate = load_candidate(target, loaded(), context, context_file, work_dir)
            except Exception as e:
                report_broken(console, e, target, work_dir)
                # The fix may be in a file the last working version never imported.
                files = None
                if _running(current_run):
                    notice(console, "Not reloaded", "still running the last working version")
                else:
                    fail(console, "The app does not load", "fix it and save")
                continue

            await _stop(console, current_run)
            current_run = _start(console, candidate, options)
            files = tracked()
    except asyncio.CancelledError:
        # Stopped (Ctrl+C). The app is stopped here, while a second Ctrl+C is
        # still asyncio's to take: leaving it to the closing loop makes the next
        # one kill the teardown halfway.
        if _running(current_run):
            notice(console, "Stopping", "Ctrl+C again to force")
            await _stop(console, current_run)
        raise


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
    force_mesh: ForceMeshOption = False,
    deep: Annotated[
        bool,
        typer.Option(
            "--deep",
            help=(
                "Also watch the packages installed for development (editable installs "
                "and linked checkouts), and reload them with the app"
            ),
        ),
    ] = False,
    context: ContextOption = None,
    context_file: ContextFileOption = None,
) -> None:
    """Runs the app in dev mode (with hot reloading)

    A change to the app or to a module of this folder it imports reloads it: those
    modules are imported anew and the App they declare then is run. Other files in
    the folder are not its business. A change that does not
    load is reported and the last working version keeps running. While it runs,
    each task the app takes is shown with how it ended.
    """

    console = get_console(ctx)
    configure_logging(log_level.value)
    work_dir = get_work_dir(ctx)
    try:
        parsed = parse_target(target, work_dir)
    except TargetError as e:
        cli_error(str(e))

    with interruptible(console):
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
