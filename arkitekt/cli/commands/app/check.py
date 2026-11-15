"""Checking an app: everything a run would refuse, found without running it."""

import inspect
import json
import os
import warnings
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Annotated, Any

import typer
from arkitekt_spec.actions import ComponentContext
from arkitekt_spec.declare.agents.dependency import prepare_dependency_variables
from arkitekt_spec.blok.catalogs import checking_catalogs
from arkitekt_spec.blok.catalogs.fetch import CatalogUnavailable, resolve_catalog
from arkitekt_spec.blok.vocabulary import BlokError
from arkitekt_spec.declare.blok.action import action_blok_id
from arkitekt_spec.declare.catalogs import CatalogWarning
from arkitekt_spec.declare.demands import DemandFinding, check_demands
from rich.console import Console
from rich.markup import escape

from arkitekt.app.terminal import done, fail, notice
from arkitekt.cli.commands.app.inspect.utils import run_snapshot_or_exit
from arkitekt.cli.offline import offline
from arkitekt.cli.options import JsonOption, LogLevel, LogLevelOption
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit, project_frame
from arkitekt.cli.utils import configure_logging, human_console, json_stdout
from arkitekt.cli.vars import get_console, get_work_dir

REPORT_VERSION = 3
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
    catalog: str | None = None,
    assets: Iterable[str] | None = None,
) -> dict[str, Any]:
    """What a blok's reads and calls resolve against, as the BSX core takes it (``BlokCheckScope``).

    Field names as the models spell them (snake_case), like the corpus' ``scope``: an editor
    completes ``deps.<key>``, ``args.<key>`` and the locals from it. A local's kind is as
    declared; the core infers the rest from the tree. ``catalog`` is the one the blok is
    written for (its address, or the name of one the app declared); null: the base catalog.
    """
    return {
        "kind": kind,
        "context": context,
        "dependencies": _dumped(dependencies),
        "locals": _dumped(locals_),
        "queries": _dumped(queries),
        "subscriptions": _dumped(subscriptions),
        "args": list(args) if args is not None else None,
        "catalog": catalog,
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
                        catalog=declaration.catalog,
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
                            catalog=blok.catalog,
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


def action_records(registry: Any) -> list[dict[str, Any]]:  # noqa: ANN401
    """Each action the app declares: where, and the hash of its definition, which is the hash the
    server finds it by whichever agent provides it (``call remote``'s ``hash_of``)."""
    from arkitekt_spec import definition_hash

    records: list[dict[str, Any]] = []
    for interface, implementation in registry.implementations.items():
        declared = registry.declared_implementations.get(interface)
        file, line = _declared_at(declared.function) if declared is not None else (None, None)
        records.append(
            _compact(
                {
                    "interface": interface,
                    "name": implementation.definition.name,
                    "hash": definition_hash(implementation.definition),
                    "file": file,
                    "line": line,
                }
            )
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


def demand_record(finding: DemandFinding) -> dict[str, Any]:
    """An unmet (or uncompared) dependency demand as a report diagnostic, at the protocol that declares it."""
    return _compact(
        {
            "level": "error" if finding.level == "error" else "info",
            "code": finding.code,
            "message": f"{finding.subject}: {finding.message}",
            "hint": (
                "The server refuses to assign a task depending on it. Change the protocol to what the app offers."
                if finding.level == "error"
                else None
            ),
            "file": finding.file,
            "call_line": finding.line,
        }
    )


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
    with_: Annotated[
        list[str] | None,
        typer.Option(
            "--with",
            help="Another app ('module[:attr]') this one depends on: what the app demands of it is "
            "compared with what it declares. Repeatable.",
        ),
    ] = None,
    catalog: Annotated[
        list[str] | None,
        typer.Option(
            "--catalog",
            help="A catalog a blok of the app is written for, by the address it is published at "
            "(https://...). It is pulled from there (or taken from what was kept the last time) "
            "before the app is imported, so its bloks are checked against it. Repeatable. The base "
            "catalog and the Orkestrator's ship with arkitekt and need none.",
        ),
    ] = None,
    offline_catalogs: Annotated[
        bool,
        typer.Option(
            "--offline-catalogs",
            help="Pull no catalog: use only what ships with arkitekt and what was kept before.",
        ),
    ] = False,
    as_json: JsonOption = False,
    log_level: LogLevelOption = LogLevel.ERROR,
) -> None:
    """Check that the app is one a run would accept, without running it

    Imports the app and validates what it declares the way a run does before it
    connects: every action's arguments and results, every structure and the
    service that resolves it. Nothing is connected or logged in to: the app is
    imported with ``run`` stubbed out, and a module that connects while it is
    imported (``with connect(app)`` at module level) is refused at that line.
    Exits with 1 and says where the problem is otherwise, so it also serves in CI.

    A blok is checked here against the catalog it is written for, which a run does
    not do: registering an app holds its bloks to the blok language alone, and
    whoever draws a blok checks it against the catalog it has. What a catalog says
    is listed as a warning (a component or prop it does not know, unless the blok
    was declared ``mode="strict"``); a component of a catalog the blok is not
    written for is an error. The base catalog, which every renderer draws, and
    the Orkestrator's ship with arkitekt. Any other is named with --catalog and
    pulled from the address it is published at: over https only, read as data,
    and kept for the next check.

    With --with, the protocols the app declares are also compared with the apps
    they are directed at: an action or state the other app does not offer, or
    offers with other ports, is an error, as the server refuses to assign a task
    that depends on it. A protocol directed at an app that was not given is not
    checked.

    With --json the report is printed on stdout instead (everything else goes to
    stderr); with --json-out the same findings are written to a file too, each with its rule
    code, the blok and node it is about and the line that declared it: what an
    editor needs to underline it. The file is written however the check ends, and
    what the app's modules print never reaches it.
    """
    configure_logging(log_level.value)
    console = human_console(get_console(ctx), as_json)
    with json_stdout(as_json) as emit:
        _check(ctx, target, json_out, console, emit, with_ or [], catalog or [], pull=not offline_catalogs)


def _check(
    ctx: typer.Context,
    target: str,
    json_out: Path | None,
    console: Console,
    emit: Callable[[Any], None],
    others: list[str],
    catalogs: list[str] | None = None,
    *,
    pull: bool = True,
) -> None:
    """What ``check`` does; ``emit`` prints the report when --json asked for it."""

    def report_to(report: dict[str, Any]) -> None:
        if json_out is not None:
            write_report(json_out, report)
        emit(report)

    report: dict[str, Any] = {
        "version": REPORT_VERSION,
        "ok": False,
        "app": None,
        "bloks": [],
        "protocols": [],
        "structures": [],
        "diagnostics": [],
    }
    # Made known before the app is imported: a blok is read against its catalog as it is declared.
    for address in catalogs or []:
        try:
            resolve_catalog(address, fetch=pull, refresh=pull)
        except CatalogUnavailable as error:
            notice(console, escape(f"{error}: what it adds to the base catalog is not checked"))
    with warnings.catch_warnings(record=True) as caught, checking_catalogs():
        warnings.simplefilter("always", CatalogWarning)
        try:
            with offline():
                app = load_app_or_exit(ctx, target)
                report["app"] = {"identifier": app.identifier, "version": app.version}
                snapshot = run_snapshot_or_exit(app)
                providers = {other.identifier: other.registry for other in (load_app_or_exit(ctx, o) for o in others)}
        except typer.Exit as exit_:
            # cli_error raised the exit while handling what went wrong: that is its context.
            findings = [warning for warning in caught if issubclass(warning.category, CatalogWarning)]
            report["diagnostics"] = [warning_record(warning) for warning in findings]
            if exit_.__context__ is not None:
                report["diagnostics"].append(error_record(exit_.__context__, get_work_dir(ctx)))
            report_to(report)
            raise
    findings = [warning for warning in caught if issubclass(warning.category, CatalogWarning)]
    for warning in findings:
        notice(console, escape(str(warning.message)))
    report.update(
        ok=True,
        bloks=blok_records(snapshot.registry),
        actions=action_records(snapshot.registry),
        protocols=protocol_records(snapshot.registry),
        structures=structure_records(snapshot.registry),
        diagnostics=[warning_record(warning) for warning in findings],
    )
    # Only asked for with --with: without another app there is nothing to compare with.
    demands = check_demands(app.registry, providers) if providers else []
    unmet = [finding for finding in demands if finding.level == "error"]
    report["diagnostics"].extend(demand_record(finding) for finding in demands)
    for finding in demands:
        said = escape(f"{finding.subject}: {finding.message}")
        where = escape(f"{finding.file}:{finding.line}") if finding.file else None
        (fail if finding.level == "error" else notice)(console, said, where)
    if unmet:
        report["ok"] = False
        report_to(report)
        raise typer.Exit(code=1)
    report_to(report)
    summary = summarize(snapshot.registry)
    if findings:
        summary += f" · {_counted(len(findings), 'warning')}"
    done(
        console,
        f"{escape(app.identifier)} {escape(app.version)} is valid",
        summary,
    )
