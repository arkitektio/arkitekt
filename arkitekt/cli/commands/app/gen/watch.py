from typing import Optional

import typer

from arkitekt.cli.errors import cli_error
from arkitekt.cli.vars import get_work_dir


def watch(
    ctx: typer.Context,
    project: Optional[str] = typer.Argument(None),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        help="The config to use",
    ),
) -> None:
    """Watch your projects documents and automatically generate code when they change

    This command will watch all the projects in your config file and automatically
    generate code when the documents change. This is useful for development.

    """
    app_directory = get_work_dir(ctx)

    from turms.run import scan_folder_for_single_config, load_projects_from_configpath
    from turms.cli.main import watch_projects

    config = config or scan_folder_for_single_config(app_directory)
    if not config:
        cli_error(
            f"No GraphQL config file found in {app_directory}. Create a graphql.config.yaml there (see the turms docs), or point at one with --config."
        )

    projects = load_projects_from_configpath(config)
    if project:
        projects = {key: value for key, value in projects.items() if key == project}

    watch_projects(projects, title="Arkitekt Code Watch")
