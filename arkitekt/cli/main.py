import rich_click as click
import asyncio
from arkitekt.cli.init import Manifest, load_manifest, write_manifest
import subprocess
from rich.console import Console
from rich.progress import Progress, TextColumn
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
import os
import sys



console = Console()

logo = """
            _    _ _       _    _   
  __ _ _ __| | _(_) |_ ___| | _| |_ 
 / _` | '__| |/ / | __/ _ \ |/ / __|
| (_| | |  |   <| | ||  __/   <| |_ 
 \__,_|_|  |_|\_\_|\__\___|_|\_\\__|
                                                                   
"""

welcome = """
Welcome to Arkitekt. Arkitekt is a framework for building beautiful and fast (serverless) APIs around
your python code.
To get started, we need some information about your app. You can always change this later.
"""


template_app = '''
from arkitekt import register

@register()
def test_func(a: int, b: int) -> int:
    """Add two numbers

    This function adds two numbers and returns the result.

    Args:
        a (int): The first number
        b (int): The second number

    Returns:
        int: The returned number
    """
    return a + b

'''


default_docker_file = '''
FROM python:3.8-slim-buster


RUN pip install arkitekt==0.4.23


RUN mkdir /app
COPY . /app
WORKDIR /app

'''




click.rich_click.HEADER_TEXT = logo
click.rich_click.ERRORS_EPILOGUE = "To find out more, visit [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]"
click.rich_click.USE_RICH_MARKUP = True


def compile_scopes():

    return ["read", "write"]


def compile_builders():

    return ["arkitekt.builders.easy", "arkitekt.builders.port"]

def compile_runtimes():

    return ["nvidia", "standard"]

@click.group()
@click.pass_context
def cli(ctx):
    """Arkitekt is a framework for building beautiful and fast (serverless) APIs around
    your python code. 
    It is build on top of Rekuest and is designed to be easy to use."""

    sys.path.append(os.getcwd())
    pass



@cli.group()
def run():
    """ Runs the arkitekt app (using a builder)"""
    pass

@run.command()
@click.option('--url', help='The fakts url for connection', default="http://localhost:8000/f/")
@click.option('--public_url', help='The fakts public_url for connection', default="http://localhost:8000/f/")
@click.option('--instance_id',"-i", help='The fakts instance_id for connection', default="main")
def easy(url, public_url, instance_id):
    """Runs the arkitekt app using the easy builder, which is the default builder
    
    This builder is the default builder for all script based apps. It is designed to be easy to use and
    to get started with. It is not recommended to use this builder for production apps.
    """

    from arkitekt.cli.run import run_costum, run_easy, run_port
    manifest = load_manifest()
    if not manifest:
        raise click.ClickException("No manifest found. Please run `arkitekt init` first before deploying an arkitekt app.")

    asyncio.run(run_easy(manifest.entrypoint, manifest.identifier, manifest.version, url, public_url, instance_id))

@run.command()
@click.option('--url', help='The fakts url for connection')
@click.option('--token', help='The fakts token for connection')
def port(url, token):
    """Runs the arkitekt app"""

    from arkitekt.cli.run import run_costum, run_easy, run_port
    manifest = load_manifest()
    if not manifest:
        raise click.ClickException("No manifest found. Please run `arkitekt init` first before deploying an arkitekt app.")

    asyncio.run(run_port(manifest.entrypoint, manifest.identifier, manifest.version, url, token ))

@run.command()
@click.option('--builder', help='The builder used to construct the app', type=click.Choice(compile_builders()), default="arkitekt.builders.easy")
def custom(builder):
    """Runs the arkitekt app"""


    from arkitekt.cli.run import run_costum, run_easy, run_port
    manifest = load_manifest()
    if not manifest:
        raise click.ClickException("No manifest found. Please run `arkitekt init` first before deploying an arkitekt app.")

    asyncio.run(run_costum(manifest.entrypoint, manifest.identifier, manifest.version, manifest.entrypoint, builder=builder))



@cli.command()
@click.option('--builder', help='The builder used to construct the app', type=click.Choice(compile_builders()), default="arkitekt.builders.easy")
def dev(builder):
    """Runs the arkitekt app"""

    from arkitekt.cli.dev import dev_module
    manifest = load_manifest()
    if not manifest:
        raise click.ClickException("No manifest found. Please run `arkitekt init` first before deploying an arkitekt app.")

    asyncio.run(dev_module(manifest.identifier, manifest.version, manifest.entrypoint, builder=builder))


@cli.command()
@click.option('--app', prompt='The module path', help='The module path', default="app")
def scan(app):

    from arkitekt.cli.scan import scan_module
    """Scans your arkitekt app for leaking variables"""
    variables = scan_module(app)

    if not variables:
        click.echo("No dangerous variables found. You are good to go!")
        return

    for key, value in variables.items():
        click.echo(f"{key}: {value}")

@cli.group()
def deploy():
    """ Deploys the arkitekt app to a specific platform (like port)"""
    pass





def search_username_in_docker_info(docker_info: str):
    for line in docker_info.splitlines():
        if "Username" in line:
            return line.split(":")[1].strip()


@deploy.command()
@click.option('--version', help='The version of your app')
@click.option('--dockerfile', help='The dockerfile to use')
@click.option('--nopush', help='Skip push')
@click.option('--tag', help='The tag to use')
@click.option('--runtime', help='The runtime to use', type=click.Choice(compile_runtimes()))
@click.option('--nodefs', help='Do not inspect definitions', is_flag=True)
def port(version, dockerfile, nopush, tag, runtime, nodefs):
    """Deploys the arkitekt app to port"""

    from arkitekt.cli.deploy import generate_deployment

    manifest = load_manifest()
    if not manifest:
        raise click.ClickException("No manifest found. Please run `arkitekt init` first before deploying an arkitekt app.")


    entrypoint = manifest.entrypoint

    if not os.path.exists(f"Dockerfile"):
        if click.confirm('Dockerfile does not exists. Do you want to generate a template Dockerfile?'):
            with open(f"Dockerfile", "w") as f:
                f.write(default_docker_file)    
                console.print("Dockerfile generated. Please edit it to your needs. And restart the deployment.")
                return 


    md = Panel("Deploying to Port", subtitle="This may take a while...", subtitle_align="right")
    console.print(md)
    version = version or manifest.version
    identifier = manifest.identifier
    entrypoint = manifest.entrypoint

    if version == "dev":
        raise click.ClickException("You cannot deploy a dev version. Please change the version in your manifest. Or use the --version flag.")

    with console.status("Searching username"):
        docker_info = subprocess.check_output(["docker", "info"]).decode("utf-8")
        username = search_username_in_docker_info(docker_info)
        if not username:
            raise click.ClickException("Could not find username in docker info. Have you logged in? Try 'docker login'")


    tag = tag or click.prompt("The tag to use", default=f"{username}/{manifest.identifier}:{version}")     
    runtime = runtime or click.prompt("The runtime to use", type=click.Choice(compile_runtimes()), default="standard")


    deployed = {
        "runtime": runtime,
    }

    md = Panel("Building Docker Container")
    console.print(md)

    docker_run = subprocess.run(["docker", "build", "-t", tag, "-f", dockerfile or "Dockerfile", "."])
    if docker_run.returncode != 0:
        raise click.ClickException("Could not build docker container")

    if not nopush:
        md = Panel("Pushing Docker Container")
        console.print(md)
        docker_run = subprocess.run(["docker", "push", tag])
        if docker_run.returncode != 0:
            raise click.ClickException("Could not push docker container")



    deployed["docker"] = tag

    generate_deployment(identifier, version, entrypoint, deployed, "arkitekt.deployers.port.dockerbuild", manifest.scopes, with_definitions=not nodefs)


def prompt_scopes():
    used_scopes = []
    scopes = compile_scopes()

    while click.confirm("Do you want to add a scope?"):
        scope = click.prompt("The scope to use", type=click.Choice(scopes), show_choices=True)
        used_scopes.append(scope)

    return used_scopes



@cli.command()
@click.option('--identifier', help='The identifier of your app')
@click.option('--version', help='The version of your app')
@click.option('--entrypoint', help='The version of your app')
@click.option('--author', help='The author of your app')
@click.option('--builder', help='The builder used to construct the app')
@click.option('--scopes', "-s", help='The scope of the app', type=click.Choice(compile_scopes()), multiple=True)
def init(identifier, version, author, entrypoint, builder, scopes):
    """Initializes the arkitekt app"""

    md = Panel(logo + welcome, title="Welcome to Arkitekt", title_align="center")
    console.print(md)

    oldmanifest = load_manifest()

    if oldmanifest:
        if not click.confirm('Do you want to overwrite your old configuration'):
            return



    manifest = Manifest(
            identifier=identifier or click.prompt("Your apps identifier", default=getattr(oldmanifest, "identifier", os.path.basename(os.getcwd()))),
            version=version or click.prompt("The apps version", default=getattr(oldmanifest, "version", "dev")),
            entrypoint=entrypoint or click.prompt("The module path", default=getattr(oldmanifest, "entrypoint", "app")),
            author=author or click.prompt("The apps author", default=getattr(oldmanifest, "author", "john doe")),
            builder=builder or click.prompt("The builder to use", default=getattr(oldmanifest, "builder", "arkitekt.builders.easy")),
            scopes=scopes or prompt_scopes()
        )

    entrypoint = manifest.entrypoint

    if not os.path.exists(f"{entrypoint}.py"):
        if click.confirm('Entrypoint does not exists. Do you want to generate a python file?'):
            with open(f"{entrypoint}.py", "w") as f:
                f.write(template_app)


    write_manifest(manifest)


if __name__ == '__main__':
    cli()
   