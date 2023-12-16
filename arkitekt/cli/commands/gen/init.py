import os
import shutil
import rich_click as click
from arkitekt.cli.options import *


@click.command()
@with_boring
@with_choose_services
@with_graphql_config
@with_api_path
@with_graphql_config
@with_docuements
@with_schemas
def init(boring, service, config, documents, schemas, overwrite_config, path):
    """Initialize code generation for the arkitekt app

    Code generation for API's is done with the help of GraphQL Code Generation
    that is powered by turms. This command initializes the code generation for
    the app. It creates the necessary folders and files for the code generation
    to work. It also creates a graphql config file that is used by turms to
    generate the code.

    """
    app_directory = os.getcwd()

    if documents:
        os.makedirs(os.path.join(app_directory, "documents"), exist_ok=True)
    if schemas:
        os.makedirs(os.path.join(app_directory, "schemas"), exist_ok=True)
    if path:
        os.makedirs(os.path.join(app_directory, path), exist_ok=True)

    # Initializing the config
    projects = {}

    for service, version in service:
        config_path = build_relative_dir("configs", service, f"{version}.yaml")
        documents_path = build_relative_dir("documents", service, version)
        schema_path = build_relative_dir("schemas", service, f"{version}.graphql")

        if schemas:
            if os.path.exists(schema_path):
                try:
                    shutil.copyfile(
                        schema_path,
                        os.path.join(app_directory, "schemas", f"{service}.graphql"),
                    )
                except FileExistsError:
                    if click.confirm(
                        f"Schema for {service} {version} already exists. Do you want to overwrite?"
                    ):
                        shutil.copytree(
                            documents_path,
                            os.path.join(app_directory, "documents", service),
                            dirs_exist_ok=True,
                        )
            else:
                get_console().print(f"[red]No schema found for {service} {version}[/]")

        if documents:
            if os.path.exists(documents_path):
                try:
                    shutil.copytree(
                        documents_path,
                        os.path.join(app_directory, "documents", service),
                    )
                except FileExistsError:
                    if click.confirm(
                        f"Documents for {service} {version} already exist. Do you want to overwrite them?"
                    ):
                        shutil.copytree(
                            documents_path,
                            os.path.join(app_directory, "documents", service),
                            dirs_exist_ok=True,
                        )

            else:
                get_console().print(f"[red]No schema found for {service} {version}[/]")

        project = yaml.load(open(config_path, "r"), Loader=yaml.FullLoader)
        if schemas:
            project["schema"] = "schemas/" + service + ".graphql"
        if documents:
            project["documents"] = "documents/" + service + "/**/*.graphql"

        project["extensions"]["turms"]["out_dir"] = path
        project["extensions"]["turms"]["generated_name"] = f"{service}.py"

        projects[service] = project

    if overwrite_config:
        graph_config_path = os.path.join(app_directory, config)
        yaml.safe_dump(
            {"projects": projects}, open(graph_config_path, "w"), sort_keys=False
        )
        get_console().print(f"Config file written to {graph_config_path}")
