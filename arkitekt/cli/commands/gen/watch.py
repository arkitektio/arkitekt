import rich_click as click
import os


@click.command()
@click.argument("project", default=None, required=False)
@click.option(
    "--config", help="The config to use", type=click.Path(exists=True), default=None
)
def watch(project, config):
    """Watch the project for changes in graphql docuemnts and compile them automatically"""
    app_directory = os.getcwd()

    from turms.run import scan_folder_for_single_config, load_projects_from_configpath
    from turms.cli.main import watch_projects

    config = config or scan_folder_for_single_config(app_directory)
    if not config:
        raise click.ClickException(
            f"No config file found. Please run `arkitekt gen init` in {app_directory} to create a default config file or specify a config file with the --config flag"
        )

    projects = load_projects_from_configpath(config)
    if project:
        projects = {key: value for key, value in projects.items() if key == project}

    watch_projects(projects, title="Arkitekt Code Watch")
