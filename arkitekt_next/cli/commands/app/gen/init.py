from importlib import import_module
import os
import shutil
from typing import Annotated, List, Optional

import typer
import yaml

from arkitekt_next.cli.constants import compile_services
from arkitekt_next.cli.errors import cli_error
from arkitekt_next.cli.interactive import require_interactive
from arkitekt_next.cli.ui import construct_codegen_welcome_panel
from arkitekt_next.cli.utils import build_relative_dir
from arkitekt_next.cli.vars import get_console, get_manifest, get_work_dir
from arkitekt_next.service_registry import get_default_service_registry


def check_services(value: List[str]) -> List[str]:
    """Validate the chosen services against the dynamically compiled service list."""
    available = compile_services()
    for service in value:
        if service not in available:
            raise typer.BadParameter(
                f"{service!r} is not one of {', '.join(available)}."
            )
    return value


def init(
    ctx: typer.Context,
    boring: Annotated[
        bool,
        typer.Option("--boring", help="Should we skip the welcome message?"),
    ] = False,
    services: Annotated[
        List[str],
        typer.Option(
            "--services",
            "-s",
            help="The services to create the codegen for",
            callback=check_services,
        ),
    ] = [],
    config: Annotated[
        str,
        typer.Option("--config", "-c", help="The name of the configuration file"),
    ] = "graphql.config.yaml",
    documents: Annotated[
        bool,
        typer.Option("--documents", "-d", help="With documents"),
    ] = True,
    schemas: Annotated[
        bool,
        typer.Option("--schemas", help="Should we copy the schemas"),
    ] = True,
    path: Annotated[
        Optional[str],
        typer.Option(
            "--path",
            "-p",
            help="The path of the api to be generated (default: api). Prompted if omitted.",
        ),
    ] = None,
    seperate_doc_dirs: Annotated[
        bool,
        typer.Option(
            "--seperate-doc-dirs",
            "-sd",
            help="Should we generate seperate dirs for the documents?",
        ),
    ] = False,
) -> None:
    """Initialize code generation for the arkitekt_next app

    Code generation for API's is done with the help of GraphQL Code Generation
    that is powered by turms. This command initializes the code generation for
    the app. It creates the necessary folders and files for the code generation
    to work. It also creates a graphql config file that is used by turms to
    generate the code.

    """
    console = get_console(ctx)

    # Welcome panel side-effect (previously the --boring option callback).
    if not boring:
        console.print(construct_codegen_welcome_panel())

    manifest = get_manifest(ctx)

    entrypoint = manifest.entrypoint

    with console.status("Loading entrypoint module..."):
        try:
            import_module(entrypoint)
        except ModuleNotFoundError as e:
            console.print(f"Could not find entrypoint module {entrypoint}")
            raise e



    app_directory = get_work_dir(ctx)

    # --path is prompted only when omitted; guard so a non-TTY run never blocks
    # on the option prompt (default is used as the prompt pre-fill).
    if path is None:
        require_interactive(
            "Choosing the api output path",
            hint="Pass --path to set it non-interactively (default: api).",
        )
        path = typer.prompt(
            "Where should we generate the api? (relative to the current directory)",
            default="api",
        )

    app_api_path = os.path.join(app_directory, path)
    app_documents = os.path.join(app_directory, "documents")

    app_schemas = os.path.join(app_directory, "schemas")

    os.makedirs(app_documents, exist_ok=True)
    os.makedirs(app_schemas, exist_ok=True)
    os.makedirs(app_api_path, exist_ok=True)

    # Initializing the config
    projects = {}

    registry = get_default_service_registry()

    chosen_services = registry.service_builders

    if services:
        chosen_services = {
            key: service
            for key, service in registry.service_builders.items()
            if key in services
        }
    else:
        require_interactive(
            "`gen init`",
            hint="Pass --service to choose the service non-interactively.",
        )
        available = ", ".join(chosen_services.keys())
        service = typer.prompt(
            f"Choose a service to initialize the project for ({available})"
        )
        if service not in chosen_services:
            cli_error(f"Unknown service '{service}'. Available: {available}")

        chosen_services = {service: chosen_services[service]}

    if os.path.exists(config):
        require_interactive(
            "`gen init`",
            hint="Remove or move the existing GraphQL config to run non-interactively.",
        )
        if typer.confirm(
            f"GraphQL Config file already exists. Do you want to merge your choices?"
        ):
            file = yaml.load(open(config, "r"), Loader=yaml.FullLoader)
            projects = file.get("projects", {})
            typer.echo(
                f"Merging {','.join(chosen_services.keys())} in {','.join(projects.keys())}..."
            )

    has_done_something = False

    for key, service in chosen_services.items():
        try:

            schema, project = service.get_graphql_schema(), service.get_turms_project()

            if not schema or not project:
                get_console(ctx).print(f"[red]No schema or project found for {key} [/]")
                continue

            if key in projects:
                get_console(ctx).print(f"[red]Project {key} already exists [/]")
                require_interactive(
                    "`gen init`",
                    hint="Remove the existing project to run non-interactively.",
                )
                if not typer.confirm("Do you want to overwrite it?"):
                    continue

            has_done_something = True

            if documents:
                os.makedirs(os.path.join(app_documents, key), exist_ok=True)
                if seperate_doc_dirs:
                    os.makedirs(
                        os.path.join(app_documents, key, "queries"), exist_ok=True
                    )
                    os.makedirs(
                        os.path.join(app_documents, key, "mutations"), exist_ok=True
                    )
                    os.makedirs(
                        os.path.join(app_documents, key, "subscriptions"), exist_ok=True
                    )

            if schemas:
                out_path = os.path.join(app_schemas, key + ".schema.graphql")
                with open(out_path, "w") as f:
                    f.write(schema)

            if schemas:
                project["schema"] = os.path.join(app_schemas, key + ".schema.graphql")
            if documents:
                project["documents"] = (
                    os.path.join(app_documents, key) + "/**/*.graphql"
                )

            project["extensions"]["turms"]["out_dir"] = path
            project["extensions"]["turms"]["generated_name"] = f"{key}.py"
            del project["extensions"]["turms"]["documents"]
            del project["schema_url"]

            projects[key] = project

        except Exception as e:
            cli_error(
                f"Failed to initialize project for {key}. Error: {e}"
            )

    if has_done_something:
        graph_config_path = os.path.join(app_directory, config)
        yaml.safe_dump(
            {"projects": projects}, open(graph_config_path, "w"), sort_keys=False
        )
        get_console(ctx).print(f"Config file written to {graph_config_path}")
    else:
        get_console(ctx).print("No projects initialized")
        get_console(ctx).print("Exiting...")
