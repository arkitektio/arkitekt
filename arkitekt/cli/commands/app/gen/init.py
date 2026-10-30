import os
from typing import Annotated, Any, List, Optional

import typer
import yaml

from arkitekt.cli.commands.app.inspect.utils import run_snapshot_or_exit
from arkitekt.cli.errors import cli_error
from arkitekt.cli.target import DEFAULT_TARGET, TargetArgument, load_app_or_exit
from arkitekt.cli.vars import get_console, get_work_dir

GEN_HINT = "Generate the code with [b]uvx --with <service packages> turms gen[/b] (or [b]turms watch[/b])."


def gen_hint(packages: List[str]) -> str:
    """How to run turms for these services' projects.

    turms imports each service's client while it generates (the client plugin),
    so the isolated uvx environment needs the service packages next to turms.
    """
    withs = " ".join(f"--with {package}" for package in packages)
    return f"Generate the code with [b]uvx {withs} turms gen[/b] (or [b]turms watch[/b])."


def _app_project(name: str, project: dict[str, Any], api: str) -> dict[str, Any]:
    """Point a service's own turms project at this app's schema copy, documents and api.

    The service's project generates the service package itself: its schema is the
    server's URL, its documents and output live in the package, and it dumps its
    configuration and schema next to the code. The app's project keeps the plugins,
    scalars and stylers (what makes the code fit the service's client) and swaps
    everything that says where things are.
    """
    turms = dict(project["extensions"]["turms"])
    turms.pop("documents", None)
    turms["out_dir"] = api
    turms["generated_name"] = f"{name}.py"
    turms["dump_configuration"] = False
    turms["dump_schema"] = False
    # An external module's sibling project lives in the service's repo, not in
    # this config; the module itself is installed with the service, so it stays.
    turms["external_modules"] = [
        {**external, "from_project": None}
        for external in turms.get("external_modules") or []
    ]
    return {
        "schema": f"schemas/{name}.graphql",
        "documents": f"graphql/{name}/**/*.graphql",
        "extensions": {"turms": turms},
    }


def init(
    ctx: typer.Context,
    target: TargetArgument = DEFAULT_TARGET,
    services: Annotated[
        Optional[List[str]],
        typer.Option(
            "--service",
            "-s",
            help="A service to set up codegen for (repeatable; default: every service the app declares that ships a turms project)",
        ),
    ] = None,
    api: Annotated[
        str,
        typer.Option("--api", help="Where turms writes the generated code, relative to the app"),
    ] = "api",
    config: Annotated[
        str,
        typer.Option("--config", "-c", help="The name of the GraphQL config file"),
    ] = "graphql.config.yaml",
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Replace projects the config already has"),
    ] = False,
) -> None:
    """Write a turms GraphQL config for the services this app uses.

    For every service the app declares that ships a schema and a turms project,
    this copies the schema to [b]schemas/<service>.graphql[/b], creates
    [b]graphql/<service>/[/b] for your documents and adds a project to the GraphQL
    config. Projects already in the config are kept. It never runs turms: write
    your operations, then run [b]uvx --with <service> turms gen[/b]: turms
    imports the service's client while it generates.
    """
    console = get_console(ctx)
    app_directory = get_work_dir(ctx)

    declared = run_snapshot_or_exit(load_app_or_exit(ctx, target)).services
    if services:
        unknown = [s for s in services if s not in declared]
        if unknown:
            cli_error(
                f"The app declares no service {', '.join(unknown)}. Available: {', '.join(declared) or 'none'}"
            )
        declared = {name: declared[name] for name in services}

    config_path = os.path.join(app_directory, config)
    projects: dict[str, Any] = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            projects = (yaml.safe_load(f) or {}).get("projects", {}) or {}

    written: List[str] = []
    for name, service in declared.items():
        schema, project = service.get_graphql_schema(), service.get_turms_project()
        if not schema or not project:
            console.print(f"[dim]{name}: ships no schema or turms project, skipped[/]")
            continue
        if name in projects and not force:
            console.print(f"[yellow]{name}: already in {config}, kept (pass --force to replace it)[/]")
            continue

        os.makedirs(os.path.join(app_directory, "schemas"), exist_ok=True)
        os.makedirs(os.path.join(app_directory, "graphql", name), exist_ok=True)
        with open(os.path.join(app_directory, "schemas", f"{name}.graphql"), "w", encoding="utf-8") as f:
            f.write(schema)
        projects[name] = _app_project(name, project, api)
        written.append(name)

    if not written:
        cli_error(f"No project written to {config}.")

    with open(config_path, "w") as f:
        yaml.safe_dump({"projects": projects}, f, sort_keys=False)

    console.print(f"Wrote {', '.join(written)} to {config_path}")
    console.print("Write your operations in [b]graphql/<service>/[/b].")
    console.print(gen_hint([name for name in declared if name in projects]))
