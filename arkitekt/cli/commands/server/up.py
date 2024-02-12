import rich_click as click
from click import Context
from dokker.projects.dokker import DokkerProject
from dokker.loggers.print import PrintLogger
from dokker.deployment import Deployment
from typing import Optional
import os
from .utils import compile_options
from rich.table import Table
from rich.live import Live
from arkitekt.cli.vars import get_console
from arkitekt.deployed import deployment
import webbrowser


DEFAULT_REPO_URL = (
    "https://raw.githubusercontent.com/jhnnsrs/konstruktor/master/repo/channels.json"
)


@click.command()
@click.option(
    "--name",
    help="The name of the deployment",
    default=None,
    required=False,
    type=click.Choice(compile_options()),
)
@click.pass_context
def up(
    ctx: Context,
    name: Optional[str] = None,
) -> None:
    """
    Ups a deployment

    Up starts your deployment. This will create all containers and networks
    needed for your deployment. If you have not run arkitekt server init
    before, this will fail.


    """
    if not name:
        options = compile_options()
        if not options:
            raise click.ClickException(
                "No deployments found. Please run arkitekt server init first"
            )

        name = options[0]

    with deployment(name) as d:
        d.up(detach=True)

        t = d.get_config()

        orkestrator_link = f'http://127.0.0.1:{t.orkestrator.port}/?endpoint=localhost:{t.lok.port}'

        table = Table(title="Deployment")
        table.add_column("Name")
        table.add_column("Value")
        table.add_row("Name", t.name)
        table.add_row("LokServer", "http://localhost:" + str(t.lok.port))
        table.add_row("Orkestrator", orkestrator_link)

        

        console = get_console(ctx)
        console.print("Deployment is up and running")
        console.print(table)
        webbrowser.open(orkestrator_link)



