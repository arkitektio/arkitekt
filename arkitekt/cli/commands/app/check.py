"""Checking an app: everything a run would refuse, found without running it."""

import json
import os
import warnings
from pathlib import Path
from typing import Annotated, Any

import typer
from arkitekt_spec.actions import ComponentContext
from arkitekt_spec.blok.vocabulary import BlokError
from arkitekt_spec.declare.blok.action import action_blok_id
from arkitekt_spec.declare.catalogs import CatalogWarning
from rich.markup import escape

from arkitekt.app.terminal import done, notice
from arkitekt.cli.commands.app.inspect.utils import run_snapshot_or_exit
from arkitekt.cli.offline import offline
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit, project_frame
from arkitekt.cli.vars import get_console, get_work_dir

REPORT_VERSION = 1
"""The shape of a ``--json-out`` report; raised when a field changes meaning or goes."""


def _counted(count: int, what: str) -> str:
    return f"{count} {what}{'' if count == 1 else 's'}"


def summarize(registry: Any) -> str:  # noqa: ANN401
    """What an app declares, in one line: ``3 actions · 1 state · uses mikro``."""
    parts: list[str] = [_counted(len(registry.implementations), "action")]
    states = len(registry.state_registry_schemas)
    if states:
        parts.append(_counted(states, "state"))
    services = sorted(registry.services)
    if services:
        parts.append(f"uses {', '.join(services)}")
    return " · ".join(parts)


def _compact(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if value is not None}


def warning_record(warning: warnings.WarningMessage) -> dict[str, Any]:
    """A recorded :class:`CatalogWarning` as a report diagnostic, at the line that declared its blok."""
    message = warning.message
    finding = message.finding if isinstance(message, CatalogWarning) else None
    return _compact(
        {
            "level": finding.level if finding is not None else "warning",
            "code": finding.code if finding is not None else None,
            "message": finding.message if finding is not None else str(message),
            "hint": finding.hint if finding is not None else None,
            "node": finding.path if finding is not None else None,
            "line": finding.line if finding is not None else None,
            "column": finding.column if finding is not None else None,
            "blok": message.blok if isinstance(message, CatalogWarning) else None,
            "file": os.path.abspath(warning.filename),
            "call_line": warning.lineno,
        }
    )


def error_record(error: BaseException, work_dir: str) -> dict[str, Any]:
    """What stopped the check, as a report diagnostic, at the user's line it came from.

    A refused blok keeps its code, the node it refuses and its line and column in the BSX;
    a syntax error is placed where Python says. Anything else is placed at the deepest frame of
    the user's own code (:func:`~arkitekt.cli.target.project_frame`).
    """
    record: dict[str, Any] = {"level": "error", "message": f"{type(error).__name__}: {error}"}
    if isinstance(error, SyntaxError) and error.filename:
        record.update(file=os.path.abspath(error.filename), call_line=error.lineno, message=f"SyntaxError: {error.msg}")
        return record
    if isinstance(error, BlokError):
        record.update(
            code=error.code,
            message=error.message,
            hint=error.hint,
            node=error.node,
            line=error.line,
            column=error.column,
        )
    frame = project_frame(error, work_dir)
    if frame is not None:
        record.update(file=os.path.abspath(frame.filename), call_line=frame.lineno)
    return _compact(record)


def blok_records(registry: Any) -> list[dict[str, Any]]:  # noqa: ANN401
    """Each blok the app declares with the BSX it was written as, for a reader to find it by.

    An app blok also says where it was declared; an action's blok is named
    :func:`~arkitekt_spec.declare.blok.action.action_blok_id`, and its warnings say where.
    """
    records: list[dict[str, Any]] = []
    for key, declaration in registry.registered_bloks.items():
        at = declaration.declared_at
        records.append(
            _compact(
                {
                    "blok": key,
                    "context": ComponentContext(declaration.context).value,
                    "source": declaration.source,
                    "file": os.path.abspath(at.filename) if at is not None else None,
                    "call_line": at.lineno if at is not None else None,
                }
            )
        )
    for interface, implementation in registry.implementations.items():
        for blok in implementation.definition.bloks or ():
            records.append(
                _compact(
                    {
                        "blok": action_blok_id(interface, blok.context),
                        "context": ComponentContext(blok.context).value,
                        "source": blok.source,
                    }
                )
            )
    return records


def write_report(path: Path, report: dict[str, Any]) -> None:
    """Write ``report`` to ``path`` whole: a reader never sees half of it."""
    partial = path.with_name(f".{path.name}.partial")
    partial.write_text(json.dumps(report, indent=2))
    os.replace(partial, path)


def check(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    json_out: Annotated[
        Path | None,
        typer.Option(
            "--json-out",
            help="Also write what the check found to this file as JSON, for an editor to place in the source.",
        ),
    ] = None,
) -> None:
    """Check that the app is one a run would accept, without running it.

    Imports the app and validates what it declares the way a run does before it
    connects: every action's arguments and results, every structure and the
    service that resolves it. Nothing is connected or logged in to: the app is
    imported with ``run`` stubbed out, and a module that connects while it is
    imported (``with connect(app)`` at module level) is refused at that line.
    Exits with 1 and says where the problem is otherwise, so it also serves in CI.

    What does not block a run is listed as a warning: a blok using a component or
    prop its catalog does not know (unless it was declared ``mode="strict"``), or
    an operation no catalog provides.

    With --json-out the same findings are written to a file too, each with its rule
    code, the blok and node it is about and the line that declared it: what an
    editor needs to underline it. The file is written however the check ends, and
    what the app's modules print never reaches it.
    """
    console = get_console(ctx)
    report: dict[str, Any] = {"version": REPORT_VERSION, "ok": False, "app": None, "bloks": [], "diagnostics": []}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", CatalogWarning)
        try:
            with offline():
                app = load_app_or_exit(ctx, target)
                report["app"] = {"identifier": app.identifier, "version": app.version}
                snapshot = run_snapshot_or_exit(app)
        except typer.Exit as exit_:
            # cli_error raised the exit while handling what went wrong: that is its context.
            if json_out is not None:
                findings = [warning for warning in caught if issubclass(warning.category, CatalogWarning)]
                report["diagnostics"] = [warning_record(warning) for warning in findings]
                if exit_.__context__ is not None:
                    report["diagnostics"].append(error_record(exit_.__context__, get_work_dir(ctx)))
                write_report(json_out, report)
            raise
    findings = [warning for warning in caught if issubclass(warning.category, CatalogWarning)]
    for warning in findings:
        notice(console, escape(str(warning.message)))
    if json_out is not None:
        report.update(
            ok=True,
            bloks=blok_records(snapshot.registry),
            diagnostics=[warning_record(warning) for warning in findings],
        )
        write_report(json_out, report)
    summary = summarize(snapshot.registry)
    if findings:
        summary += f" · {_counted(len(findings), 'warning')}"
    done(
        console,
        f"{escape(app.identifier)} {escape(app.version)} is valid",
        summary,
    )
