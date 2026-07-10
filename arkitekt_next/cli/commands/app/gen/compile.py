from typing import List, Optional

import typer

from arkitekt_next.cli.errors import cli_error
from arkitekt_next.cli.vars import get_work_dir


def compile(
    ctx: typer.Context,
    projects: Optional[List[str]] = typer.Argument(None),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        help="The config to use",
    ),
) -> None:
    """Genererate the code of a project"

    Uses a previously generated graphql-config.yaml file to generate the code for a or multiple projects.
    If no project is specified, all projects will be generated.


    """
    app_directory = get_work_dir(ctx)

    from turms.run import scan_folder_for_single_config, load_projects_from_configpath
    from turms.cli.main import generate_projects

    config = config or scan_folder_for_single_config(app_directory)
    if not config:
        cli_error(
            f"No config file found. Please run `arkitekt_next gen init` in {app_directory} to create a default config file or specify a config file with the --config flag"
        )

    parsing_projects = load_projects_from_configpath(config)
    if projects:
        parsing_projects = {
            key: value for key, value in parsing_projects.items() if key in projects
        }

    if not parsing_projects:
        cli_error(
            f"No projects found with the name '{projects}'. Available Projects: {', '.join(parsing_projects.keys())}"
        )

    generate_projects(parsing_projects, title="ArkitektNext Compile")

    pass
