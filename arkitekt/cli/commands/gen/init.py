import os
import shutil
import rich_click as click
from arkitekt.cli.options import (
    with_documents,
    with_graphql_config,
    with_api_path,
    with_boring,
    with_choose_services,
    with_schemas,
    with_seperate_document_dirs,
)
import yaml
from arkitekt.cli.utils import build_relative_dir
from arkitekt.cli.vars import get_console, get_manifest


@click.command()
@with_seperate_document_dirs
@with_boring
@with_choose_services
@with_graphql_config
@with_api_path
@with_schemas
@with_graphql_config
@with_documents
@click.pass_context
def init(ctx, boring, services, config, documents, schemas, path, seperate_doc_dirs):
    """Initialize code generation for the arkitekt app

    Code generation for API's is done with the help of GraphQL Code Generation
    that is powered by turms. This command initializes the code generation for
    the app. It creates the necessary folders and files for the code generation
    to work. It also creates a graphql config file that is used by turms to
    generate the code.

    """
    app_directory = os.getcwd()

    app_api_path = os.path.join(app_directory, path)
    app_documents = os.path.join(app_directory, "graphql", "documents")

    app_schemas = os.path.join(app_directory, "graphql", "schemas")

    if documents:
        os.makedirs(app_documents, exist_ok=True)
    if schemas:
        os.makedirs(app_schemas, exist_ok=True)
    if path:
        os.makedirs(app_api_path, exist_ok=True)

    # Initializing the config
    projects = {}

    base_config = yaml.load(
        open(build_relative_dir("configs", "base.yaml"), "r"), Loader=yaml.FullLoader
    )

    for service in services:
        schema_path = build_relative_dir("schemas", f"{service}.schema.graphql")

        if documents:
            os.makedirs(os.path.join(app_documents, service), exist_ok=True)
            if seperate_doc_dirs:
                os.makedirs(
                    os.path.join(app_documents, service, "queries"), exist_ok=True
                )
                os.makedirs(
                    os.path.join(app_documents, service, "mutations"), exist_ok=True
                )
                os.makedirs(
                    os.path.join(app_documents, service, "subscriptions"), exist_ok=True
                )

        if schemas:
            if os.path.exists(schema_path):
                try:
                    shutil.copyfile(
                        schema_path,
                        os.path.join(app_schemas, service + ".graphql"),
                    )
                except FileExistsError:
                    if click.confirm(
                        f"Schema for {service} already exist. Do you want to overwrite them?"
                    ):
                        shutil.copyfile(
                            schema_path,
                            os.path.join(app_schemas, service + ".graphql"),
                        )
            else:
                get_console(ctx).print(f"[red]No schema found for {service} [/]")

        try:
            project = base_config["projects"][service]
        except KeyError:
            get_console(ctx).print(f"[red]No config found for {service} [/]")
            continue

        if schemas:
            project["schema"] = os.path.join(app_schemas, service + ".graphql")
        if documents:
            project["documents"] = (
                os.path.join(app_documents, service) + "/**/*.graphql"
            )

        project["extensions"]["turms"]["out_dir"] = path
        project["extensions"]["turms"]["generated_name"] = f"{service}.py"

        projects[service] = project

    if os.path.exists(config):
        if not click.confirm(
            f"GraphQL Config file already exists. Do you want to overwrite?"
        ):
            click.echo("Aborting...")
            ctx.abort()

    graph_config_path = os.path.join(app_directory, config)
    yaml.safe_dump(
        {"projects": projects}, open(graph_config_path, "w"), sort_keys=False
    )
    get_console(ctx).print(f"Config file written to {graph_config_path}")
