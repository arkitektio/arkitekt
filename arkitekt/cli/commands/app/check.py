"""Checking an app: everything a run would refuse, found without running it."""

import inspect
import json
import os
import warnings
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated, Any

import typer
from arkitekt_spec.actions import ComponentContext
from arkitekt_spec.declare.agents.dependency import prepare_dependency_variables
from arkitekt_spec.blok.vocabulary import BlokError
from arkitekt_spec.declare.blok.action import action_blok_id
from arkitekt_spec.declare.catalogs import CatalogWarning
from rich.markup import escape

from arkitekt.app.terminal import done, notice
from arkitekt.cli.commands.app.inspect.utils import run_snapshot_or_exit
from arkitekt.cli.offline import offline
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit, project_frame
from arkitekt.cli.vars import get_console, get_work_dir

REPORT_VERSION = 2
"""The shape of a ``--json-out`` report; raised when a field changes meaning or goes.

2: every blok carries its ``scope``, an action's blok where its action was declared, and the
report lists the dependency ``protocols`` the app declares. It also lists the ``structures``
the app knows, by the class behind each identifier; a reader takes their absence as knowing none."""


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


def _dumped(models: Iterable[Any]) -> list[dict[str, Any]]:
    return [model.model_dump(mode="json", exclude_none=True) for model in models]


def _declared_at(obj: Any) -> tuple[str | None, int | None]:  # noqa: ANN401
    """The file and first line (its first decorator's) of a function or class, if it has source."""
    try:
        target = inspect.unwrap(obj) if callable(obj) and not isinstance(obj, type) else obj
        file = inspect.getsourcefile(target)
        _, line = inspect.getsourcelines(target)
    except (OSError, TypeError):
        return None, None
    return (os.path.abspath(file) if file else None), line


def scope_record(
    *,
    kind: str,
    context: str,
    dependencies: Iterable[Any] = (),
    locals_: Iterable[Any] = (),
    queries: Iterable[Any] = (),
    subscriptions: Iterable[Any] = (),
    args: Iterable[str] | None = None,
    catalogs: Iterable[str] = (),
    module: str | None = None,
    assets: Iterable[str] | None = None,
) -> dict[str, Any]:
    """What a blok's reads and calls resolve against, as the BSX core takes it (``BlokCheckScope``).

    Field names as the models spell them (snake_case), like the corpus' ``scope``: an editor
    completes ``deps.<key>``, ``args.<key>`` and the locals from it. A local's kind is as
    declared; the core infers the rest from the tree.
    """
    return {
        "kind": kind,
        "context": context,
        "dependencies": _dumped(dependencies),
        "locals": _dumped(locals_),
        "queries": _dumped(queries),
        "subscriptions": _dumped(subscriptions),
        "args": list(args) if args is not None else None,
        "catalogs": list(catalogs),
        "module": module,
        "assets": sorted(assets) if assets is not None else None,
    }


def blok_records(registry: Any) -> list[dict[str, Any]]:  # noqa: ANN401
    """Each blok the app declares with the BSX it was written as, for a reader to find it by,
    and its scope.

    An app blok says where it was declared, an action's blok where its action was (the
    decorator's line); an action's blok is named
    :func:`~arkitekt_spec.declare.blok.action.action_blok_id`.
    """
    # Built again for the dependencies a blok's ``self`` reads; what it warns was told already.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            built = registry.get_declared_bloks()
        except Exception:  # noqa: BLE001 - the check passed; a scope is a convenience
            built = {}
    assets = list(registry.registered_assets)
    records: list[dict[str, Any]] = []
    for key, declaration in registry.registered_bloks.items():
        at = declaration.declared_at
        context = ComponentContext(declaration.context).value
        blok = built.get(key)
        records.append(
            _compact(
                {
                    "blok": key,
                    "context": context,
                    "source": declaration.source,
                    "file": os.path.abspath(at.filename) if at is not None else None,
                    "call_line": at.lineno if at is not None else None,
                    "scope": scope_record(
                        kind="action_logo" if context == ComponentContext.ACTION_LOGO.value else "agent",
                        context=context,
                        dependencies=blok.dependencies if blok is not None else (),
                        locals_=declaration.locals,
                        queries=declaration.queries,
                        subscriptions=declaration.subscriptions,
                        args=[port.key for port in declaration.args],
                        catalogs=(blok.catalogs or ()) if blok is not None else declaration.catalogs,
                        module=declaration.module,
                        assets=assets,
                    ),
                }
            )
        )
    for interface, implementation in registry.implementations.items():
        declared = registry.declared_implementations.get(interface)
        file, line = _declared_at(declared.function) if declared is not None else (None, None)
        for blok in implementation.definition.bloks or ():
            context = ComponentContext(blok.context).value
            records.append(
                _compact(
                    {
                        "blok": action_blok_id(interface, blok.context),
                        "context": context,
                        "source": blok.source,
                        "file": file,
                        "call_line": line,
                        "scope": scope_record(
                            kind="action",
                            context=context,
                            dependencies=implementation.dependencies,
                            locals_=blok.locals,
                            queries=blok.queries,
                            subscriptions=blok.subscriptions,
                            args=[port.key for port in implementation.definition.args or ()],
                            catalogs=blok.catalogs,
                            module=blok.module,
                        ),
                    }
                )
            )
    return records


def structure_records(registry: Any) -> list[dict[str, Any]]:  # noqa: ANN401
    """The Python class behind each identifier this app knows, its services' included: what an editor
    writes when a port names one. An enum spelled as a Literal, or a nested class, has no name to import."""
    structures = registry.structure_registry
    records: list[dict[str, Any]] = []
    for kind, known in (
        ("STRUCTURE", structures.identifier_structure_map),
        ("MODEL", structures.identifier_model_map),
        ("ENUM", structures.identifier_enum_map),
        ("MEMORY_STRUCTURE", structures.identifier_memory_structure_map),
    ):
        for identifier, fullfilled in known.items():
            cls = fullfilled.cls
            name, module = getattr(cls, "__qualname__", None), getattr(cls, "__module__", None)
            if isinstance(name, str) and isinstance(module, str) and "." not in name:
                records.append(
                    _compact({"identifier": identifier, "kind": kind, "name": name, "module": module, "file": _declared_at(cls)[0]})
                )
    return records


def protocol_records(registry: Any) -> list[dict[str, Any]]:  # noqa: ANN401
    """Each dependency protocol the app declares: where, the dependency it stands for, and the
    action parameters that take it.

    ``dependency`` is the protocol's ``AgentDependencyInput`` as the models spell it (snake_case),
    keyed by its interface: what an editor asks a server for the agents that would satisfy it.
    """
    structures = registry.structure_registry
    used: dict[Any, list[dict[str, str]]] = {}
    for interface, declared in registry.declared_implementations.items():
        try:
            variables = prepare_dependency_variables(declared.function, structures).dependency_variables
        except Exception:  # noqa: BLE001 - registering it already said what is wrong
            continue
        for key, cls in variables.items():
            used.setdefault(cls, []).append({"action": interface, "key": key})
    records: list[dict[str, Any]] = []
    for cls, protocol in structures.protocols.items():
        file, line = _declared_at(cls)
        records.append(
            _compact(
                {
                    "name": cls.__qualname__,
                    "interface": protocol.interface,
                    "file": file,
                    "line": line,
                    "dependency": protocol.to_dependency_input(protocol.interface).model_dump(
                        mode="json", exclude_none=True
                    ),
                    "used_by": used.get(cls, []),
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
    report: dict[str, Any] = {
        "version": REPORT_VERSION,
        "ok": False,
        "app": None,
        "bloks": [],
        "protocols": [],
        "structures": [],
        "diagnostics": [],
    }
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
            protocols=protocol_records(snapshot.registry),
            structures=structure_records(snapshot.registry),
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
