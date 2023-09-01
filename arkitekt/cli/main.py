import rich_click as click
import asyncio
from arkitekt.cli.init import Manifest, load_manifest, write_manifest
import subprocess
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
import os
import sys
from .utils import build_relative_dir
import shutil
import getpass
from .ui import construct_leaking_group
from .build import docker_file_wizard
from .types import Requirement
from .inspect import inspect_requirements
import semver
import yaml

console = Console()

logo = """
            _    _ _       _    _   
  __ _ _ __| | _(_) |_ ___| | _| |_ 
 / _` | '__| |/ / | __/ _ \ |/ / __|
| (_| | |  |   <| | ||  __/   <| |_ 
 \__,_|_|  |_|\_\_|\__\___|_|\_\\__|
                                                                   
"""

welcome = (
    "Welcome to Arkitekt. Arkitekt is a bioimage analysis framework for building"
    " beautiful and fast (serverless) APIs around your python code. It is buid on top of "
    "composable packages like mikro, fluss and rekuest, which allow you to build simple"
    " apps with ease."
)


default_docker_file = """
FROM python:3.8-slim-buster


RUN pip install arkitekt==0.4.23


RUN mkdir /app
COPY . /app
WORKDIR /app

"""


click.rich_click.HEADER_TEXT = logo
click.rich_click.ERRORS_EPILOGUE = "To find out more, visit [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]"
click.rich_click.USE_RICH_MARKUP = True


def parse_semver(param: str, loaded=False):
    if not semver.Version.is_valid(param):
        if loaded:
            raise click.ClickException(
                "Manifest version incorrect, please update your manifest to a valid semver version  [link=https://semver.org]semver[/link]."
            )

        raise click.ClickException(
            f"Arkitekt versions need to follow semantic versioning. Please choose a correct format (examples: 0.0.0, 0.1.0, 0.0.0-alpha.1)"
        )
    return semver.Version.parse(param)


def compile_scopes():
    return ["read", "write"]


def compile_requirements():
    return [Requirement.GPU.value]


def compile_builders():
    return ["arkitekt.builders.easy", "arkitekt.builders.port"]


def compile_runtimes():
    return ["nvidia", "standard"]


def compile_schema_versions():
    z = build_relative_dir("schemas")
    return [
        os.path.basename(f) for f in os.listdir(z) if os.path.isdir(os.path.join(z, f))
    ]


def compile_configs():
    z = build_relative_dir("configs")
    return [
        os.path.basename(f) for f in os.listdir(z) if os.path.isdir(os.path.join(z, f))
    ]


def compile_templates():
    z = build_relative_dir("templates")
    return [
        os.path.basename(f).split(".")[0]
        for f in os.listdir(z)
        if os.path.isfile(os.path.join(z, f))
    ]


def compile_versions():
    z = build_relative_dir("versions")
    return [
        os.path.basename(f).split(".")[0]
        for f in os.listdir(z)
        if os.path.isfile(os.path.join(z, f))
    ]


with_token = click.option(
    "--token",
    "-t",
    help="The token for the fakts instance",
    envvar="FAKTS_TOKEN",
    required=False,
)
with_version = click.option(
    "--version",
    "-v",
    help="Override the version of the app",
    envvar="ARKITEKT_VERSION",
)

with_log_level = click.option(
    "--log",
    "-l",
    help="Override the logging level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    envvar="ARKITEKT_LOG_LEVEL",
)


with_skip_cache = click.option(
    "--no-cache",
    "-nc",
    is_flag=True,
    default=False,
    help="Should we skip the cache",
    envvar="ARKITEKT_NO_CACHE",
)

with_instance_id = click.option(
    "--instance-id",
    "-i",
    default="main",
    help="The token for the fakts instance",
    envvar="REKUEST_INSTANCE",
)

with_log_level = click.option(
    "--log-level",
    "-l",
    default="INFO",
    help="The token for the fakts instance",
    envvar="ARKITEKT_LOG_LEVEL",
)


with_builder = click.option(
    "--builder",
    "-b",
    default="arkitekt.builders.easy",
    help="The builder for this run",
    envvar="ARKITEKT_BUILDER",
)

headless = click.option(
    "--headless",
    "-h",
    is_flag=True,
    default=False,
    help="Should we start headless",
    envvar="ARKITEKT_HEADLESS",
)


@click.group()
@click.pass_context
def cli(ctx):
    """Arkitekt is a framework for building beautiful and fast (serverless) APIs around
    your python code.
    It is build on top of Rekuest and is designed to be easy to use."""
    sys.path.append(os.getcwd())
    pass


@cli.group()
@click.pass_context
def run(ctx):
    """Runs the arkitekt app (using a builder) in stable mode

    You can choose between different builders to run your app. The default builder is the easy builder, which is
    designed to be easy to use and to get started with. It is not recommended to use this builder for
    production apps.

    """
    manifest = load_manifest()
    if not manifest:
        raise click.ClickException(
            "No manifest found. Please run `arkitekt init` first before deploying an arkitekt app."
        )

    ctx.ensure_object(dict)
    ctx.obj["manifest"] = manifest


@run.command("prod")
@click.option(
    "--url",
    help="The fakts url for connection",
    default="http://localhost:8000",
    envvar="FAKTS_URL",
)
@with_builder
@with_token
@with_instance_id
@headless
@with_log_level
@with_version
@with_skip_cache
@click.pass_context
def prod(ctx, **kwargs):
    """Runs the arkitekt app in production mode (with a builder)

    \n
    By default, the easy builder is used, which is designed to be easy to use and to get started with.
    It is not recommended to use this builder for 'real production' apps.
    """

    from arkitekt.cli.run import run_production

    manifest = load_manifest()
    if not manifest:
        raise click.ClickException(
            "No manifest found. Please run `arkitekt init` first before deploying an arkitekt app."
        )

    asyncio.run(run_production(ctx.obj["manifest"], **kwargs))


@run.command()
@click.option(
    "--url",
    help="The fakts url for connection",
    default="http://localhost:8000",
    envvar="FAKTS_URL",
)
@with_builder
@with_token
@with_instance_id
@headless
@with_version
@with_log_level
@with_skip_cache
@click.option(
    "--deep",
    help="Should we check the whole directory for changes and reload them for dependencie",
    is_flag=True,
)
@click.pass_context
def dev(ctx, **kwargs):
    """Runs the arkitekt app in dev mode (with hot reloading)"""
    from arkitekt.cli.dev import run_dev

    asyncio.run(run_dev(ctx.obj["manifest"], **kwargs))


@cli.command()
@click.option("--entrypoint", help="The module path", default=None)
def scan(entrypoint):
    """Scans your arkitekt app for leaking variables"""
    from arkitekt.cli.scan import scan_module

    if not entrypoint:
        manifest = load_manifest()
        entrypoint = manifest.entrypoint

    variables = scan_module(entrypoint)

    if not variables:
        console.print(
            Panel(
                "No dangerous variables found. You are good to go!  🎉",
                style="green",
                border_style="green",
                title="Arkitekt Scan",
            )
        )
        return

    group = construct_leaking_group(variables)

    panel = Panel(
        group, title="Arkitekt Scan", expand=True, border_style="red", style="red"
    )
    console.print(panel)


def check_gen_boring(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    if not value:
        md = Panel(
            logo
            + "[white]"
            + welcome
            + "\n\n"
            + "[bold green]Let's setup your codegen environment",
            title="Welcome to Arkitekt Codegen",
            title_align="center",
            border_style="green",
            style="green",
        )
        console.print(md)
    return value


@cli.group()
def gen():
    """Use the arkitekt code generation modules to generate code"""
    try:
        import turms

        pass
    except ImportError as e:
        raise click.ClickException(
            "Turms is not installed. Please install turms first before using the arkitekt codegen."
        ) from e


def check_overwrite_config(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    config = ctx.params["config"]
    if os.path.exists(config) and not value:
        should_overwrite = click.confirm(
            f"GraphQL Config file already exists. Do you want to overwrite?"
        )
        return should_overwrite

    return value


@gen.command()
@click.option(
    "--boring",
    help="Should we skip the welcome message?",
    is_flag=True,
    default=False,
    callback=check_gen_boring,
)
@click.option(
    "--service",
    "-s",
    help="The services to create the codegen for",
    nargs=2,
    multiple=True,
    type=click.Tuple(
        [click.Choice(compile_configs()), click.Choice(compile_versions())]
    ),
    default=[("mikro", "v1"), ("fluss", "v1"), ("rekuest", "v1")],
)
@click.option(
    "--config",
    "-c",
    help="The name of the configuration file",
    type=str,
    default="graphql.config.yaml",
)
@click.option(
    "--path",
    "-c",
    help="The path of the api to be generated",
    prompt="Where should we generate the api? (relative to the current directory)",
    type=str,
    default="api",
)
@click.option(
    "--overwrite-config",
    "-o",
    help="Should we overwrite the config file if it already exists",
    is_flag=True,
    default=False,
    callback=check_overwrite_config,
)
@click.option(
    "--documents",
    "-d",
    help="With documents",
    is_flag=True,
    default=True,
)
@click.option(
    "--schemas",
    "-s",
    help="Should we copy the schemas",
    is_flag=True,
    default=True,
)
def init(boring, service, config, documents, schemas, overwrite_config, path):
    """Initialize code generation for the arkitekt app"""
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
        config_path = build_relative_dir(f"configs", service, f"{version}.yaml")
        documents_path = build_relative_dir(f"documents", service, version)
        schema_path = build_relative_dir(f"schemas", service, f"{version}.graphql")

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
                console.print(f"[red]No schema found for {service} {version}[/]")

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
                console.print(f"[red]No schema found for {service} {version}[/]")

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
        print(f"Config file written to {graph_config_path}")


@gen.command()
@click.argument("projects", default=None, required=False, nargs=-1)
@click.option(
    "--config",
    help="The config to use",
    type=click.Path(exists=True),
    default=None,
)
def compile(projects, config):
    """Initialize code generation for the arkitekt app"""
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


@gen.command()
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

    pass


def search_username_in_docker_info(docker_info: str):
    for line in docker_info.splitlines():
        if "Username" in line:
            return line.split(":")[1].strip()


@cli.group()
@click.pass_context
def port(ctx):
    """Deploy the arkitekt app with Port

    The port deployer is an arkitekt plugin service, which allows you to deploy your arkitekt app to
    any arkitekt instance and make it instantly available to the world. Port uses docker to containerize
    your application and will publish it locally to your dockerhub account, and mark it locally as
    deployed. People can then use your github repository to deploy your app to their arkitekt instance.

    """
    manifest = load_manifest()
    if not manifest:
        raise click.ClickException(
            "No manifest found. Please run `arkitekt init` first before accessing these features."
        )

    ctx.ensure_object(dict)
    ctx.obj["manifest"] = manifest


@port.command()
@click.option("--build", help="The build to use", type=str, default="latest")
@click.option("--tag", help="The tag to use")
def publish(build, tag):
    """Deploys aa previous build to dockerhub"""

    from arkitekt.cli.deploy import (
        generate_deployment,
        check_if_manifest_already_deployed,
    )
    from arkitekt.cli.build import get_builds

    builds = get_builds()
    assert (
        build in builds
    ), f"Build {build} not found. Please run `arkitekt build` first"
    build = builds[build]

    manifest = build.manifest
    if build.manifest.version == "dev":
        raise click.ClickException(
            "You cannot deploy a dev version. Please run `arkitekt version` first to set a version"
        )

    check_if_manifest_already_deployed(manifest)
    docker_info = subprocess.check_output(["docker", "info"]).decode("utf-8")
    username = search_username_in_docker_info(docker_info)
    if not username:
        username = click.prompt(
            "Could not find username in docker info. Please provide your docker username"
        )

    tag = tag or click.prompt(
        "The tag to use",
        default=f"{username}/{build.manifest.identifier}:{build.manifest.version}",
    )

    md = Panel("Building Docker Container")
    console.print(md)

    deployed = {}

    docker_run = subprocess.run(["docker", "tag", build.build_id, tag])
    if docker_run.returncode != 0:
        raise click.ClickException("Could not retag docker container")

    console.print(md)
    docker_run = subprocess.run(["docker", "push", tag])
    if docker_run.returncode != 0:
        raise click.ClickException("Could not push docker container")

    deployed["docker"] = tag

    generate_deployment(
        build,
        tag,
        with_definitions=False,
    )


@port.command()
@click.option("--dockerfile", help="The dockerfile to use", default="Dockerfile")
@click.option(
    "--builder", help="The port builder to use", default="arkitekt.builders.port"
)
def build(dockerfile, builder):
    """Builds the arkitekt app to docker"""

    from arkitekt.cli.build import generate_build
    import uuid

    build_id = str(uuid.uuid4())

    manifest = load_manifest()
    if not manifest:
        raise click.ClickException(
            "No manifest found. Please run `arkitekt init` first before building an arkitekt app."
        )

    if not os.path.exists(dockerfile):
        raise click.ClickException(
            f"Dockerfile {dockerfile} does not exist. Please create a dockerfile first (e.g. with the port wizard command)."
        )

    md = Panel(
        "Building for Port", subtitle="This may take a while...", subtitle_align="right"
    )

    md = Panel("Building Docker Container")
    console.print(md)

    docker_run = subprocess.run(
        ["docker", "build", "-t", build_id, "-f", dockerfile or "Dockerfile", "."]
    )
    if docker_run.returncode != 0:
        raise click.ClickException("Could not build docker container")

    generate_build(builder, build_id, manifest)


def check_overwrite_dockerfile(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    app_file = ctx.params["dockerfile"]
    if os.path.exists(app_file) and not value:
        should_overwrite = click.confirm(
            f"Docker already exists. Do you want to overwrite?", abort=True
        )

    return value


def check_build_boring(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    if not value:
        md = Panel(
            logo + "[white]" + welcome + "\n\n" + "[bold green]Let's build your app",
            title="Welcome to Arkitekt",
            title_align="center",
            border_style="green",
            style="green",
        )
        console.print(md)
    return value


@port.command()
@click.option("--dockerfile", help="The dockerfile to generate", default="Dockerfile")
@click.option(
    "--boring",
    help="Should we skip the welcome message?",
    is_flag=True,
    default=False,
    callback=check_build_boring,
)
@click.option(
    "--overwrite-dockerfile",
    "-o",
    help="Should we overwrite the existing Dockerfile?",
    is_flag=True,
    default=False,
    callback=check_overwrite_dockerfile,
)
def wizard(dockerfile, boring, overwrite_dockerfile):
    """Runs the port wizard to generate a dockerfile to be used with port"""

    manifest = load_manifest()
    dockfile = docker_file_wizard(manifest)

    if dockfile:
        with open(dockerfile, "w") as file:
            file.write(dockfile)


@port.command()
@click.option("--build", help="The build to use", type=str, default="latest")
@click.option(
    "--url", help="The fakts server to use", type=str, default="localhost:8000"
)
@click.option(
    "--builder", help="The builder to use", type=str, default="arkitekt.builders.easy"
)
def stage(build, url, builder):
    """Stages the latest Build for testing

    Stages the current build for testing. This will create a temporary staged version
    of the app that is run agains the local arkitekt instance. The builder will be changed
    to the easy or provided builder to ensure that the app can be run headlessly


    """
    from arkitekt.cli.build import get_builds
    import uuid

    manifest = load_manifest()
    if not manifest:
        raise click.ClickException(
            "No manifest found. Please run `arkitekt init` first before versioning an arkitekt app."
        )

    builds = get_builds()
    assert (
        build in builds
    ), f"Build {build} not found. Please run `arkitekt build` first"
    build = builds[build]
    build_id = build.build_id

    click.echo(f"Running inside docker: {manifest.identifier}:{manifest.version}")
    docker_run = subprocess.run(
        [
            "docker",
            "run",
            "-it",
            "--net",
            "host",
            "--gpus",
            "all",
            build_id,
            "arkitekt",
            "run",
            "prod",
            "--builder",
            builder,
            "--headless",
            "--url",
            url,
        ],
    )

    message_string = (
        docker_run.stdout.decode("utf-8")
        if docker_run.stdout
        else "" + docker_run.stderr.decode("utf-8")
        if docker_run.stderr
        else ""
    )

    if "No manifest found" in message_string:
        raise click.ClickException(
            "Looks like the docker container could not find the manifest. Did you mount the '.arkitekt folder' correctly?"
        )

    raise click.ClickException("Docker container exited")


@cli.group()
@click.pass_context
def manifest(ctx):
    """Updates the manifest of this app

    The manifest is used to describe the app and its rights (scopes) and requirements, to be run on the platform.
    This manifest is used to authenticate the app with the platform establishing its scopes and requirements.




    """
    manifest = load_manifest()
    if not manifest:
        raise click.ClickException(
            "No manifest found. Please run `arkitekt init` first before accessing these features."
        )

    ctx.ensure_object(dict)
    ctx.obj["manifest"] = manifest


@manifest.command()
def inspect():
    """Inspect the manifest of this app


    The manifest is used to describe the app and its rights (scopes) and requirements, to be run on the platform.
    This manifest is used to authenticate the app with the platform establishing its scopes and requirements.


    """
    manifest = load_manifest()

    table = Table.grid()
    table.add_column()
    table.add_column()
    table.add_row("Identifier", manifest.identifier)
    table.add_row("Version", manifest.version)
    table.add_row("Author", manifest.author)
    table.add_row("Logo", manifest.logo or "-")
    table.add_row("Entrypoint", manifest.entrypoint)
    table.add_row("Command", manifest.command)
    table.add_row("Scopes", ", ".join(manifest.scopes) if manifest.scopes else "-")
    table.add_row(
        "Requirements",
        ", ".join(manifest.requirements) if manifest.requirements else "-",
    )
    table.add_row("Created at", str(manifest.created_at.strftime("%Y/%m/%d %H:%M")))

    panel = Panel(
        Group("[bold green]Manifest[/]", table),
        title_align="center",
        border_style="green",
        style="white",
    )

    console.print(panel)


@manifest.group()
@click.pass_context
def version(ctx):
    """Updates the version of the arkitekt app

    Arkitekt manifests versioning follow [link=https://semver.org]semver[/link] and are used to version the app.

    """


@version.command("set")
@click.argument("VERSION", type=str, required=False)
@click.pass_context
def set_version(ctx, version):
    manifest = ctx.obj["manifest"]
    old_version = manifest.version

    if not version:
        try:
            potential_new_version = parse_semver(old_version, loaded=True).bump_patch()
        except Exception:
            potential_new_version = None

        new_version = click.prompt(
            "Please provide a new version", default=potential_new_version, type=str
        )
        version = parse_semver(new_version)
        version = new_version

    manifest.version = version
    write_manifest(manifest)
    console.print(f"Version Updated from {old_version} to {version}")


@version.command()
@click.pass_context
def patch(ctx):
    "Patches the version of the arkitekt app"
    manifest = ctx.obj["manifest"]
    old_version = manifest.version
    manifest.version = parse_semver(old_version).bump_patch()
    write_manifest(manifest)
    console.print(f"Version Updated from {old_version} to {manifest.version}")


@version.command()
@click.pass_context
def minor(ctx):
    "Patches the version of the arkitekt app"
    manifest = ctx.obj["manifest"]
    old_version = manifest.version
    manifest.version = parse_semver(old_version).bump_minor()
    write_manifest(manifest)
    console.print(f"Version Updated from {old_version} to {manifest.version}")


@version.command()
@click.pass_context
def major(ctx):
    "Patches the version of the arkitekt app"
    manifest = ctx.obj["manifest"]
    old_version = manifest.version
    manifest.version = parse_semver(old_version).bump_major()
    write_manifest(manifest)
    console.print(f"Version Updated from {old_version} to {manifest.version}")


@version.command()
@click.pass_context
def prerelease(ctx):
    "Patches the version of the arkitekt app"
    manifest = ctx.obj["manifest"]
    old_version = manifest.version
    manifest.version = parse_semver(old_version).bump_prerelease()
    write_manifest(manifest)
    console.print(f"Version Updated from {old_version} to {manifest.version}")


@version.command("build")
@click.pass_context
def bump_build(ctx):
    "Patches the version of the arkitekt app"
    manifest = ctx.obj["manifest"]
    old_version = manifest.version
    manifest.version = parse_semver(old_version).bump_build()
    write_manifest(manifest)
    console.print(f"Version Updated from {old_version} to {manifest.version}")


@manifest.group("scopes")
@click.pass_context
def scopes_group(ctx):
    """Inspect, add and remove scopes to this arkitekt app

    Scopes are rights that are granted to any arkitekt application, and correspond
    to rights that enable feature when interacting with the platform. These scopes
    provide another element of access control to the arkitekt platform, and describe
    on top of the users rights, what the application is allowed to do.

    For more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]


    """
    manifest = load_manifest()
    if not manifest:
        raise click.ClickException(
            "No manifest found. Please run `arkitekt init` first before accessing these features."
        )

    ctx.ensure_object(dict)
    ctx.obj["manifest"] = manifest


@scopes_group.command("add")
@click.argument(
    "SCOPE",
    nargs=-1,
    type=click.Choice(compile_scopes()),
)
@click.pass_context
def add_scopes(ctx, scope):
    """ "Acd scopes

    Scopes are rights that are granted to any arkitekt application, and correspond
    to rights that enable feature when interacting with the platform. These scopes
    provide another element of access control to the arkitekt platform, and describe
    on top of the users rights, what the application is allowed to do.

    For more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]


    """
    if not scope:
        raise click.ClickException("Please provide at least one scope")

    manifest = ctx.obj["manifest"]
    if scope:
        manifest.scopes = set(list(scope) + manifest.scopes)
        write_manifest(manifest)
        console.print(f"Scopes Updated to {manifest.scopes}")


@scopes_group.command("remove")
@click.argument(
    "SCOPE",
    nargs=-1,
    type=click.Choice(compile_scopes()),
)
@click.pass_context
def remove_scopes(ctx, scope):
    """Remove scopes

    Scopes are rights that are granted to any arkitekt application, and correspond
    to rights that enable feature when interacting with the platform. These scopes
    provide another element of access control to the arkitekt platform, and describe
    on top of the users rights, what the application is allowed to do.

    For more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]


    """
    if not scope:
        raise click.ClickException("Please provide at least one scope to remove")

    manifest = ctx.obj["manifest"]
    if scope:
        manifest.scopes = set(manifest.scopes) - set(scope)
        write_manifest(manifest)
        console.print(f"Scopes Updated to {manifest.scopes}")


@scopes_group.command("list")
@click.pass_context
def list_scopes(ctx):
    """List all the [i] currently [/] active scopes

    Scopes are rights that are granted to any arkitekt application, and correspond
    to rights that enable feature when interacting with the platform. These scopes
    provide another element of access control to the arkitekt platform, and describe
    on top of the users rights, what the application is allowed to do.

    For more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]


    """

    manifest = load_manifest()

    table = Table.grid()
    table.add_column("Scope")
    table.add_column("Description")
    for scope in manifest.scopes:
        table.add_row(scope, "TODO")

    panel = Panel(
        Group("[bold green]Scopes[/]", table),
        title_align="center",
        border_style="green",
        style="white",
    )

    console.print(panel)


@scopes_group.command("available")
@click.pass_context
def list_available(ctx):
    """List all the [i] available [/]  scopes

    Scopes are rights that are granted to any arkitekt application, and correspond
    to rights that enable feature when interacting with the platform. These scopes
    provide another element of access control to the arkitekt platform, and describe
    on top of the users rights, what the application is allowed to do.

    For more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]


    """

    table = Table.grid()
    table.add_column("Scope")
    table.add_column("Description")
    for scope in compile_scopes():
        table.add_row(scope, "TODO")

    panel = Panel(
        Group("[bold green]Available Scopes[/]", table),
        title_align="center",
        border_style="green",
        style="white",
    )

    console.print(panel)


@manifest.group("requirements")
@click.pass_context
def requirements_group(ctx):
    """Inspect, add and remove requirements to this arkitekt app

    Requirements are used to hint the user to have specific hardware or software installed, when
    using your application. It is also used to inform the platform about the requirements of your app,
    when installing it in its plugin sandbox. for more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]

    """
    manifest = load_manifest()
    if not manifest:
        raise click.ClickException(
            "No manifest found. Please run `arkitekt init` first before accessing these features."
        )

    ctx.ensure_object(dict)
    ctx.obj["manifest"] = manifest


@requirements_group.command("add")
@click.argument(
    "REQUIREMENTS",
    nargs=-1,
    type=click.Choice(compile_requirements()),
)
@click.pass_context
def add_requirement(ctx, requirements):
    """Add requiremenets

    Requirements are used to hint the user to have specific hardware or software installed, when
    using your application. It is also used to inform the platform about the requirements of your app,
    when installing it in its plugin sandbox. for more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]

    """
    if not requirements:
        raise click.ClickException("Please provide at least one requirement")

    manifest = ctx.obj["manifest"]
    if requirements:
        manifest.requirements = set(list(requirements) + manifest.requirements)
        write_manifest(manifest)
        console.print(f"Requirements Updated to {manifest.requirements}")


@requirements_group.command("remove")
@click.argument(
    "REQUIREMENTS",
    nargs=-1,
    type=click.Choice(compile_requirements()),
)
@click.pass_context
def remove_requirements(ctx, requirements):
    """Remove requirements

    Requirements are used to hint the user to have specific hardware or software installed, when
    using your application. It is also used to inform the platform about the requirements of your app,
    when installing it in its plugin sandbox. for more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]


    """
    if not requirements:
        raise click.ClickException("Please provide at least one requirement to remove")

    manifest = ctx.obj["manifest"]
    if requirements:
        manifest.requirements = set(manifest.requirements) - set(requirements)
        write_manifest(manifest)
        console.print(f"Requirements Updated to {manifest.requirements}")


@requirements_group.command("list")
@click.pass_context
def list_requirements(ctx):
    """Lists the [i]current[/] requirements

    Requirements are used to hint the user to have specific hardware or software installed, when
    using your application. It is also used to inform the platform about the requirements of your app,
    when installing it in its plugin sandbox. for more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]

    """

    manifest = ctx.obj["manifest"]

    table = Table(
        title="[green bold ]Requirements[/]",
        title_justify="left",
        title_style="green bold",
    )
    table.add_column("Requirement")
    table.add_column("Description")

    for scope in manifest.requirements:
        table.add_row(scope, "TODO")

    panel = Panel(
        table,
        title_align="center",
        border_style="green",
        style="white",
    )

    console.print(panel)


@requirements_group.command("available")
@click.pass_context
def list_available_requirements(ctx):
    """Lists the [i]available[/] requirements

    Requirements are used to hint the user to have specific hardware or software installed, when
    using your application. It is also used to inform the platform about the requirements of your app,
    when installing it in its plugin sandbox. for more information, please visit the [link=https://jhnnsrs.github.io/doks]https://jhnnsrs.github.io/doks[/link]

    """

    table = Table.grid()
    table.add_column("Scope")
    table.add_column("Description")
    for scope in compile_requirements():
        table.add_row(scope, "TODO")

    panel = Panel(
        Group("[bold green]Available Scopes[/]", table),
        title_align="center",
        border_style="green",
        style="white",
    )

    console.print(panel)


def prompt_scopes():
    used_scopes = []
    scopes = compile_scopes()

    scope_text = (
        "\n\n[white]Every arkitekt app is assigned specific permissions to access data and interact with the "
        "platform. These permissions are called scopes, and are additional safeguard to the user permissions. "
        "You can find a list of all available scopes "
        "[link=https://jhnnsrs.github.io/security/scopes.html]here[/link]\n\n"
        "Please try to use as [b]few[/b] scopes as possible"
    )

    panel = Panel(
        "Let's talk permissions" + scope_text,
        title_align="center",
        border_style="green",
        style="green",
    )
    console.print(panel)
    while click.confirm(" Do you want to add a scope?"):
        scope = click.prompt(
            " The scope to use", type=click.Choice(scopes), show_choices=True
        )
        used_scopes.append(scope)

    click.echo("Using scopes: " + ", ".join(used_scopes))

    return used_scopes


def prompt_requirements():
    scope_text = (
        "\n\n[white]Every arkitekt app can hint the user to have specific hardware or software installed. "
        + "These hints,and are for example used to manage the installation of your app in sandbox / cloud"
        + "environments. You can find a list of all available requirements here."
    )

    panel = Panel(
        "Let's talk permissions" + scope_text,
        title_align="center",
        border_style="green",
        style="green",
    )
    console.print(panel)
    requirements = []
    if click.confirm(
        " Do you want to automatically search for potential requirements?"
    ):
        requirements, reasons = inspect_requirements()
        if len(requirements) == 0:
            click.echo("No requirements found")
        else:
            for req, reason in zip(requirements, reasons):
                click.echo("Added requirement: \n" + req + " because " + reason)

    while click.confirm(" Do you want to manually a requirements?"):
        requirement = click.prompt(
            " The requirement to use",
            type=click.Choice(compile_requirements()),
            show_choices=True,
        )
        requirements.append(requirement)

    click.echo("Using requirements: " + ", ".join(requirements))

    return requirements


def check_overwrite(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    manifest = load_manifest()

    if load_manifest() and not value:
        should_overwrite = click.confirm(
            f"Another Arkitekt app {manifest.to_console_string()} exists already?. Do you want to overwrite?",
            abort=True,
        )
        if not should_overwrite:
            ctx.abort()
    return value


def check_overwrite_app(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    app_file = ctx.params["app"] + ".py"
    if os.path.exists(app_file) and not value:
        should_overwrite = click.confirm(
            f"App File already exists. Do you want to overwrite?"
        )
        return should_overwrite

    return value


def check_init_boring(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    if not value:
        md = Panel(
            logo + "[white]" + welcome + "\n\n" + "[bold green]Let's setup your app",
            title="Welcome to Arkitekt",
            title_align="center",
            border_style="green",
            style="green",
        )
        console.print(md)
    return value


def ensure_semver(ctx, param, value):
    """Callback to check and prompt for file overwrite."""

    if not value:
        value = click.prompt(
            "The version of your app",
            default="0.0.1",
        )

    while not semver.Version.is_valid(value):
        console.print(
            "Arkitekt versions need to follow [link=https://semver.org]semver[/link]. Please choose a correct format (examples: 0.0.0, 0.1.0, 0.0.0-alpha.1)"
        )
        value = click.prompt(
            "The version of your app",
            default="0.0.1",
        )

    return value


@cli.command()
@click.option(
    "--boring",
    help="Should we skip the welcome message?",
    is_flag=True,
    default=False,
    callback=check_init_boring,
)
@click.option(
    "--overwrite-manifest",
    help="Should we overwrite the existing manifest?",
    is_flag=True,
    default=False,
    callback=check_overwrite,
)
@click.option(
    "--template",
    help="The template to use",
    type=click.Choice(compile_templates()),
    default="simple",
)
@click.option(
    "--identifier",
    help="The identifier of your app",
    prompt="Your app name",
    default=os.path.basename(os.getcwd()),
)
@click.option(
    "--version", help="The version of your app", default="0.0.1", callback=ensure_semver
)
@click.option(
    "--author",
    help="The author of your app",
    prompt="Your name",
    default=getpass.getuser(),
)
@click.option(
    "--template",
    help="Which template to use top create entrypoint",
    prompt="Your app file template",
    type=click.Choice(compile_templates()),
    default="simple",
)
@click.option(
    "--app",
    help="The entrypoint of your app. This will be the name of the python file",
    prompt="Your app file",
    default="app",
)
@click.option(
    "--overwrite-app",
    help="The entrypoint of your app. This will be the name of the python file",
    is_flag=True,
    default=False,
    callback=check_overwrite_app,
)
@click.option(
    "--requirements",
    "-r",
    help="Hardware requirements of this app",
    type=click.Choice(compile_requirements()),
    multiple=True,
    default=[],
)
@click.option(
    "--scopes",
    "-s",
    help="The scope of the app",
    type=click.Choice(compile_scopes()),
    multiple=True,
    default=["read"],
)
def init(
    identifier,
    version,
    author,
    scopes,
    template,
    requirements,
    app,
    overwrite_manifest,
    overwrite_app,
    boring,
):
    """Initializes the arkitekt app"""
    print(identifier, version, author)
    manifest = Manifest(
        author=author,
        identifier=identifier,
        version=version,
        scopes=scopes,
        requirements=requirements,
        entrypoint=app,
    )

    with open(build_relative_dir("templates", f"{template}.py")) as f:
        template_app = f.read()

    if not os.path.exists("app") or overwrite_app:
        with open(f"{app}.py", "w") as f:
            f.write(template_app)

    write_manifest(manifest)
    if not boring:
        md = Panel(
            f"{manifest.to_console_string()} was successfully initialized\n\n"
            + "[not bold white]We are excited to see what you come up with!",
            border_style="green",
            style="green",
        )
        console.print(md)


if __name__ == "__main__":
    cli()
