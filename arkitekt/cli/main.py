import sys
import os

try:
    import rich_click as click

    from rich.console import Console
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
from arkitekt.cli.commands.server.main import server
from arkitekt.cli.commands.port.main import port
from arkitekt.cli.commands.init.main import init
from arkitekt.cli.commands.manifest.main import manifest
from arkitekt.cli.commands.inspect.main import inspect
from arkitekt.cli.commands.call.main import call
from arkitekt.cli.io import load_manifest
from arkitekt.utils import create_arkitekt_folder

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
    """Arkitekt is a framework for building safe and performant apps that then can be centrally orchestrated and managed
    in workflows.


    This is the CLI for the Arkitekt Python SDK. It allows you to create and deploy Arkitekt Apps from your python code
    as well as to run them locally for testing and development. For more information about Arkitekt, please visit
    [link=https://arkitekt.live]https://arkitekt.live[/link]
    """
    sys.path.append(os.getcwd())

    ctx.obj = {}
    console = Console()
    set_console(ctx, console)

    create_arkitekt_folder()

    manifest = load_manifest()
    if manifest:
        set_manifest(ctx, manifest)

    pass


cli.add_command(init, "init")
cli.add_command(run, "run")
cli.add_command(gen, "gen")
cli.add_command(port, "port")
cli.add_command(manifest, "manifest")
cli.add_command(inspect, "inspect")
cli.add_command(server, "server")
cli.add_command(call, "call")

if __name__ == "__main__":
    cli()
