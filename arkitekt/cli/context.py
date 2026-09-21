"""The app context a run command hands to the runner: ``--context`` / ``--context-file``.

An App that declares an app context (``App(..., app_context=Config)``) cannot run
without an instance of it, and the command line has no way to construct one on its
own. Two ways in: ``--context module:attr`` names an instance (or a zero-argument
factory of one) in the user's code, and ``--context-file config.yaml`` hands a
document to the declared class, which must then be a pydantic model. Either is
resolved before anything connects, so a missing or wrong context fails at the
prompt, not after a login.
"""

import inspect
import json
from pathlib import Path
from typing import Any, Optional

from arkitekt.app.app import App
from arkitekt.cli.errors import cli_error
from arkitekt.cli.target import TargetError, import_target, parse_target


def load_context(
    app: App[Any],
    context: Optional[str],
    context_file: Optional[Path],
    work_dir: str,
) -> Any:  # noqa: ANN401
    """The app context for a run of ``app``, from the flags; ``None`` when it declares none.

    Args:
        app: The App about to run: what it declared decides what is accepted.
        context: The ``--context`` flag, ``module:attr``.
        context_file: The ``--context-file`` flag.
        work_dir: The directory ``module`` is resolved against.

    Returns:
        An instance of the declared class, or ``None`` for an App declaring none.

    Exits:
        With guidance when both flags are given, when the App declares a context
        and neither flag is, when a flag is given to an App declaring none, or
        when what a flag names is not an instance of the declared class.
    """
    declared = app.app_context
    if context is not None and context_file is not None:
        cli_error("Pass --context or --context-file, not both.")
    if declared is None:
        if context is not None or context_file is not None:
            cli_error(
                f"App {app.identifier!r} declares no app context, so --context/--context-file "
                "have nothing to fill. Declare one: App(..., app_context=Config)."
            )
        return None
    if context is not None:
        return _from_target(app, declared, context, work_dir)
    if context_file is not None:
        return _from_file(app, declared, context_file)
    cli_error(
        f"App {app.identifier!r} declares an app context ({declared.__name__}). "
        "Pass --context module:attr or --context-file config.yaml."
    )


def _from_target(app: App[Any], declared: type, context: str, work_dir: str) -> Any:  # noqa: ANN401
    try:
        target = parse_target(context, work_dir)
    except TargetError as e:
        cli_error(f"--context: {e}")
    if target.attribute is None:
        cli_error("--context needs module:attr: the attribute holding the app context.")
    module = import_target(target)
    try:
        value = getattr(module, target.attribute)
    except AttributeError:
        cli_error(f"--context: {module.__name__} has no attribute {target.attribute!r}.")
    if not isinstance(value, declared) and callable(value):
        value = value()
        if inspect.isawaitable(value):
            cli_error("--context: a factory must return the app context, not a coroutine.")
    if not isinstance(value, declared):
        cli_error(
            f"--context: {context} is a {type(value).__name__}, but App {app.identifier!r} "
            f"declares its app context as {declared.__name__}."
        )
    return value


def _from_file(app: App[Any], declared: type, path: Path) -> Any:  # noqa: ANN401
    validate = getattr(declared, "model_validate", None)
    if validate is None:
        cli_error(
            f"App {app.identifier!r} declares its app context as {declared.__name__}, which is "
            "not a pydantic model, so --context-file cannot build it. Use --context module:attr."
        )
    text = path.read_text()
    if path.suffix.lower() in (".yaml", ".yml"):
        import yaml

        data = yaml.safe_load(text)
    elif path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        cli_error(f"--context-file: {path} is neither YAML (.yaml/.yml) nor JSON (.json).")
    if not isinstance(data, dict):
        cli_error(f"--context-file: {path} must hold a mapping of {declared.__name__}'s fields.")
    try:
        return validate(data)
    except Exception as e:  # pydantic's ValidationError, spelled out for the prompt
        cli_error(f"--context-file: {path} is not a valid {declared.__name__}: {e}")


__all__ = ["load_context"]
