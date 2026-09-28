"""Finding the app a command acts on: the ``module[:attr]`` target.

There is no project file that names the app. The app is the :class:`~arkitekt.App`
object in the user's module, found the way uvicorn finds a module's ``app``:

- ``app`` (the default, or ``$ARKITEKT_APP``) imports the module ``app``;
- ``pkg.main:api`` imports ``pkg.main`` and takes its attribute ``api``;
- ``app.py`` / ``src/app.py:api`` is a file path, relative to ``--work-dir``
  (which the root callback puts first on ``sys.path``), turned into its module name.

Without ``:attr`` the app is the module's ``app``, or its only App; several Apps and
none named ``app`` is an ambiguity the user resolves with ``:attr``.

Everything here is pure resolution: nothing connects and nothing is built. The
identity (identifier, version, scopes, ...) the CLI shows or packages is read off
the App object this returns.
"""

import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Annotated, Any, Optional

import typer

from arkitekt.app.app import App
from arkitekt.cli.errors import cli_error

#: The target used when none is given: the module ``app`` (the file ``app.py``).
DEFAULT_TARGET = "app"

#: The environment variable that sets the target when no argument is given.
TARGET_ENVVAR = "ARKITEKT_APP"

#: The positional ``module[:attr]`` argument every app command takes.
TargetArgument = Annotated[
    str,
    typer.Argument(
        envvar=TARGET_ENVVAR,
        help=(
            "The app to use, as 'module[:attr]' (like uvicorn): 'app', 'app:app', "
            "'pkg.main:api' or a file path such as 'app.py'. Resolved relative to "
            "--work-dir. Without ':attr' the module's `app`, or its only App, is used."
        ),
        show_default=True,
    ),
]

_NEW_API_EXAMPLE = (
    "    from arkitekt import App, run\n\n"
    '    app = App("my-app", "0.0.1")\n\n'
    "    @app.action\n"
    "    def my_function(x: int) -> int: ...\n\n"
    '    if __name__ == "__main__":\n'
    "        run(app)\n"
)


class TargetError(ValueError):
    """The target string cannot name a module (bad syntax, or outside the work dir)."""


class NoAppError(ValueError):
    """The target module defines no app."""


@dataclass(frozen=True)
class Target:
    """A parsed ``module[:attr]`` target.

    ``file`` is where the module's source is expected, even before it imports: the
    dev loop watches it, and has to watch it while it is still broken.
    """

    module: str
    attribute: Optional[str]
    file: str

    def __str__(self) -> str:
        return f"{self.module}:{self.attribute}" if self.attribute else self.module


def _split_attribute(target: str) -> tuple[str, Optional[str]]:
    """Split off ``:attr`` -- but not the ``:`` of a Windows drive (``C:\\app.py``)."""
    module, sep, attribute = target.rpartition(":")
    if sep and module and attribute.isidentifier():
        return module, attribute
    if sep and module and attribute == "":
        raise TargetError(f"'{target}' ends in ':' but names no attribute.")
    return target, None


def parse_target(target: str, work_dir: str) -> Target:
    """Parse ``target`` into the module to import, relative to ``work_dir``.

    A target is a file path when it ends in ``.py`` or contains a path separator;
    otherwise it is a dotted module name. A file path has to lie inside
    ``work_dir``: that is the directory on ``sys.path``, so it is the only place the
    file's module name can be derived from.

    Args:
        target: ``module[:attr]`` or ``path/to/file.py[:attr]``.
        work_dir: The directory the app lives in, which is on ``sys.path``.

    Returns:
        The module to import, the attribute (if named) and the file expected.

    Raises:
        TargetError: If the target is empty, or a path outside ``work_dir``.
    """
    raw = target.strip()
    if not raw:
        raise TargetError("The app target is empty. Pass 'module[:attr]', e.g. 'app'.")

    location, attribute = _split_attribute(raw)
    root = Path(work_dir).resolve()

    separators = [s for s in (os.sep, os.altsep, "/") if s]
    if location.endswith(".py") or any(s in location for s in separators):
        path = Path(location)
        if not path.is_absolute():
            path = root / path
        path = path.resolve()
        try:
            relative = path.relative_to(root)
        except ValueError:
            raise TargetError(
                f"'{location}' is not inside the work dir '{root}'. Pass --work-dir "
                "to the directory that contains it."
            ) from None
        if relative.suffix == ".py":
            relative = relative.with_suffix("")
        parts = relative.parts
    else:
        parts = tuple(p for p in location.strip(".").split(".") if p)

    if not parts or not all(part.isidentifier() for part in parts):
        raise TargetError(
            f"'{target}' does not name an importable module. Pass 'module[:attr]' "
            "or a path to a .py file."
        )

    module_file = root.joinpath(*parts).with_suffix(".py")
    package_init = root.joinpath(*parts, "__init__.py")
    file = package_init if not module_file.exists() and package_init.exists() else module_file
    return Target(module=".".join(parts), attribute=attribute, file=str(file))


def import_target(target: Target) -> ModuleType:
    """Import the target's module, from the work dir rather than from a stale cache.

    A module of that name imported earlier from somewhere else (another work dir in
    the same process, as in tests or an embedding tool) is dropped first, so the
    file under ``--work-dir`` is the one that is loaded.

    Args:
        target: The parsed target.

    Returns:
        The imported module.

    Raises:
        ModuleNotFoundError: If the module, or something it imports, is missing.
    """
    cached = sys.modules.get(target.module)
    if cached is not None:
        cached_file = getattr(cached, "__file__", None)
        if cached_file is None or os.path.realpath(cached_file) != os.path.realpath(target.file):
            del sys.modules[target.module]
    importlib.invalidate_caches()
    # The user's module is named by a string on the command line: this is the one
    # place an import by name is unavoidable.
    return importlib.import_module(target.module)


def find_app(module: Optional[ModuleType], attribute: Optional[str] = None) -> Optional[App[Any]]:
    """Find the App a module declares, or ``None`` if it declares none.

    With ``attribute`` that object is taken, and must be an App. Without it, the
    one named ``app`` wins; otherwise a single App (possibly under several names)
    is taken, and several are ambiguous.

    Args:
        module: The module to look in. ``None`` finds nothing.
        attribute: The name the App is held under, if the target named one.

    Returns:
        The App, or ``None`` if the module declares none.

    Raises:
        NoAppError: If ``attribute`` is given and is not an App.
        ValueError: If the module declares several Apps and none is named ``app``.
    """
    if module is None:
        return None

    if attribute is not None:
        if not hasattr(module, attribute):
            raise NoAppError(
                f"Module '{module.__name__}' has no attribute '{attribute}'. Name the "
                "attribute that holds the App, or leave ':attr' off to use its `app`."
            )
        candidate = getattr(module, attribute)
        if not isinstance(candidate, App):
            raise NoAppError(
                f"'{attribute}' in module '{module.__name__}' is not an arkitekt App "
                f"(got {type(candidate).__name__}). Declare it as:\n\n" + _NEW_API_EXAMPLE
            )
        return candidate

    apps = {name: value for name, value in vars(module).items() if isinstance(value, App)}
    if not apps:
        return None
    if "app" in apps:
        return apps["app"]
    if len({id(value) for value in apps.values()}) == 1:
        return next(iter(apps.values()))
    raise ValueError(
        f"Module '{module.__name__}' defines several apps ({', '.join(sorted(apps))}). "
        f"Choose one with 'module:attr', e.g. '{module.__name__}:{sorted(apps)[0]}'."
    )


def require_app(module: ModuleType, attribute: Optional[str] = None) -> App[Any]:
    """:func:`find_app`, where a module without an App is an error that shows the API.

    Args:
        module: The module to look in.
        attribute: The name the App is held under, if the target named one.

    Returns:
        The App.

    Raises:
        NoAppError: If the module declares no App.
    """
    app = find_app(module, attribute)
    if app is None:
        raise NoAppError(
            f"Module '{module.__name__}' defines no arkitekt App. An app module "
            "declares its own app and offers functions on it:\n\n" + _NEW_API_EXAMPLE
        )
    return app


def load_target(target: str, work_dir: str) -> tuple[App[Any], ModuleType, Target]:
    """Parse, import and resolve ``target``.

    Args:
        target: ``module[:attr]`` or ``path/to/file.py[:attr]``.
        work_dir: The directory the app lives in.

    Returns:
        The App, its module and the parsed target.

    Raises:
        TargetError, NoAppError, ValueError: As the steps do.
        Exception: Whatever importing the user's module raises.
    """
    parsed = parse_target(target, work_dir)
    module = import_target(parsed)
    return require_app(module, parsed.attribute), module, parsed


def import_target_or_exit(ctx: typer.Context, target: str) -> tuple[ModuleType, Target]:
    """Import the target's module for a command; an unimportable target exits cleanly.

    Args:
        ctx: The command's context, which holds the console and work dir.
        target: ``module[:attr]`` or ``path/to/file.py[:attr]``.

    Returns:
        The imported module and the parsed target.
    """
    from arkitekt.cli.vars import get_console, get_work_dir

    try:
        parsed = parse_target(target, get_work_dir(ctx))
    except TargetError as e:
        cli_error(str(e))
    with get_console(ctx).status(f"Loading {parsed.module}..."):
        try:
            return import_target(parsed), parsed
        except ModuleNotFoundError as e:
            # Only the target itself missing is a target problem; a missing
            # dependency of the user's module is reported as what it is.
            if e.name is not None and (
                e.name == parsed.module or parsed.module.startswith(e.name + ".")
            ):
                cli_error(
                    f"Could not find the app module '{parsed.module}' in "
                    f"'{get_work_dir(ctx)}' (expected {parsed.file}). Pass the "
                    "target as 'module[:attr]', or set --work-dir."
                )
            cli_error(f"Importing '{parsed.module}' failed: {e}")


def load_app_or_exit(ctx: typer.Context, target: str) -> App[Any]:
    """The App a command acts on; a missing module or app exits with guidance.

    Loading only imports and resolves: nothing is connected or built.

    Args:
        ctx: The command's context, which holds the console and work dir.
        target: ``module[:attr]`` or ``path/to/file.py[:attr]``.

    Returns:
        The App.
    """
    module, parsed = import_target_or_exit(ctx, target)
    try:
        return require_app(module, parsed.attribute)
    except ValueError as e:
        cli_error(str(e))


def infer_package_manager(work_dir: str) -> str:
    """``uv`` for a uv project (it has a ``uv.lock``), ``pip`` for anything else.

    The lockfile is what a uv-built image installs from, so it -- not whether uv
    happens to be on this machine -- decides how the project is packaged.

    Args:
        work_dir: The project directory.

    Returns:
        ``"uv"`` or ``"pip"``.
    """
    return "uv" if os.path.exists(os.path.join(work_dir, "uv.lock")) else "pip"
