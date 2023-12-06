import rich_click as click
import os


@click.command()
@click.argument("projects", default=None, required=False, nargs=-1)
@click.option(
    "--config",
    help="The config to use",
    type=click.Path(exists=True),
    default=None,
)
def compile(projects, config):
    """Genererate the code of a project"

    Uses a previously generated graphql-config.yaml file to generate the code for a or multiple projects.
    If no project is specified, all projects will be generated.


    """
    app_directory = os.getcwd()

    from turms.run import scan_folder_for_single_config, load_projects_from_configpath
    from turms.cli.main import generate_projects

    config = config or scan_folder_for_single_config(app_directory)
    if not config:
        raise click.ClickException(
            f"No config file found. Please run `arkitekt gen init` in {app_directory} to create a default config file or specify a config file with the --config flag"
        )

    parsing_projects = load_projects_from_configpath(config)
    if projects:
        parsing_projects = {
            key: value for key, value in parsing_projects.items() if key in projects
        }

    if not parsing_projects:
        raise click.ClickException(
            f"No projects found with the name '{projects}'. Available Projects: {', '.join(parsing_projects.keys())}"
        )

    generate_projects(parsing_projects, title="Arkitekt Compile")

    pass
