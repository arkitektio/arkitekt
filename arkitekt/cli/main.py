import sys
import os

try:
    import rich_click as click
    import semver

    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    import semver
    import watchfiles
except ImportError:
    print(
        "Arkitekt CLI is not installed, please install it first. By installing the cli, e.g with `pip install arkitekt[cli]`, you can use the `arkitekt` command."
    )
    sys.exit(1)

from arkitekt.cli.vars import *
from arkitekt.cli.constants import *
from arkitekt.cli.texts import *
from arkitekt.cli.commands.run.main import run
from arkitekt.cli.commands.gen.main import gen
from arkitekt.cli.commands.port.main import port
from arkitekt.cli.commands.init.main import init
from arkitekt.cli.commands.manifest.main import manifest
from arkitekt.cli.commands.scan.main import scan
from arkitekt.cli.io import write_manifest, load_manifest

default_docker_file = """
FROM python:3.8-slim-buster


RUN pip install arkitekt==0.4.23


RUN mkdir /app
COPY . /app
WORKDIR /app

"""


click.rich_click.HEADER_TEXT = LOGO
click.rich_click.ERRORS_EPILOGUE = ERROR_EPILOGUE
click.rich_click.USE_RICH_MARKUP = True


@click.group()
@click.pass_context
def cli(ctx):
    """Arkitekt is a framework for building beautiful and fast (serverless) APIs around
    your python code.
    It is build on top of Rekuest and is designed to be easy to use."""
    sys.path.append(os.getcwd())

    console = Console()
    set_console(console)

    manifest = load_manifest()
    if manifest:
        set_manifest(manifest)

    pass


cli.add_command(run, "run")
cli.add_command(gen, "gen")
cli.add_command(port, "port")
cli.add_command(init, "init")
cli.add_command(manifest, "manifest")
cli.add_command(scan, "scan")

if __name__ == "__main__":
    cli()
