from arkitekt.cli.types import Manifest, Packager
from arkitekt.cli.vars import get_manifest
import sys
import rich_click as click
from click import Context
import subprocess
from rich import get_console

try:
    pass
except ImportError as e:
    raise ImportError("Please install rekuest to use this feature") from e


import os


def get_base_prefix_compat() -> str:
    """Get base/real prefix, or sys.prefix if there is none."""
    return (
        getattr(sys, "base_prefix", None)
        or getattr(sys, "real_prefix", None)
        or sys.prefix
    )


def in_virtualenv() -> bool:
    """Returns True if in a virtualenv, otherwise False."""
    return get_base_prefix_compat() != sys.prefix


def pip_no_gpu(manifest: Manifest, python_version: str) -> str:
    """A function to generate a dockerfile for pip without gpu support

    Parameters
    ----------
    manifest : Manifest
        The manifest of the project
    python_version : str
        The python version to use

    Returns
    -------
    str
        The dockerfile
    """
    get_console().print("[blue]Setting up environment...[/blue]")
    if not in_virtualenv():
        click.confirm(
            "You are not in a virtual environment. Consider using a virtual environment. Do you want to continue?",
            abort=True,
        )

    if not os.path.exists(".requirements.txt") and click.confirm(
        "Do you want to freeze the dependencies the current interpreter?"
    ):
        subprocess.check_call("pip freeze > requirements.txt", shell=True)

    get_console().print("[blue]Generating Dockerfile...[/blue]")

    BASE_IMAGE = f"FROM python:{python_version}\n"
    PIP_APPENDIX = "# setup pip  environment\nCOPY ./requirements.txt /tmp/requirements.txt\nRUN pip install /tmp/requirements.yml\n"
    WORKDIR_APPENDIX = "RUN mkdir /app \nWORKDIR /app"

    dockerfile = BASE_IMAGE
    if click.confirm(
        "Do you want to install a requirements.txt with the dependencies with pip?"
    ):
        dockerfile += PIP_APPENDIX

    if click.confirm("Do you want to use the current working directory as the app?"):
        dockerfile += WORKDIR_APPENDIX

    return dockerfile


def poetry_no_gpu(manifest: Manifest, python_version: str) -> str:
    """A function to generate a dockerfile for pip without gpu support

    Parameters
    ----------
    manifest : Manifest
        The manifest of the project
    python_version : str
        The python version to use

    Returns
    -------
    str
        The dockerfile
    """
    get_console().print("[blue]Setting up environment...[/blue]")
    if not in_virtualenv():
        click.confirm(
            "You are not in a virtual environment. Consider using a virtual environment. Do you want to continue?",
            abort=True,
        )

    if click.confirm("Do you want to lock the current dependencies?"):
        subprocess.check_call("poetry lock", shell=True)

    get_console().print("[blue]Generating Dockerfile...[/blue]")

    BASE_IMAGE = f"FROM python:{python_version}\n"
    SETUP_POETRY = "# Install dependencies\nRUN pip install poetry rich\nENV PYTHONUNBUFFERED=1\n# Install Project files\nCOPY pyproject.toml /tmp\nCOPY poetry.lock /tmp\nRUN poetry config virtualenvs.create false\nWORKDIR /tmp\nRUN poetry install\n"
    WORKDIR_APPENDIX = "RUN mkdir /app\nCOPY . /app\nWORKDIR /app\n"

    dockerfile = BASE_IMAGE
    dockerfile += SETUP_POETRY

    if click.confirm("Do you want to use the current working directory as the app?"):
        dockerfile += WORKDIR_APPENDIX

    return dockerfile


CONDA_GPU = """
FROM jhnnsrs/tensorflow_conda_gpu:latest

# setup conda virtual environment
COPY ./requirements.yml /tmp/requirements.yml
RUN conda env create --name camera-seg -f /tmp/requirements.yml

RUN conda activate camera-seg   
"""


CONDA_NO_GPU = """
FROM jhnnsrs/tensorflow_conda:latest

# setup conda virtual environment
COPY ./requirements.yml /tmp/requirements.yml
RUN conda env create --name camera-seg -f /tmp/requirements.yml

RUN conda activate camera-seg
"""

BUILDERS = {
    "pip": {
        "gpu": None,
        "no-gpu": pip_no_gpu,
    },
    "conda": None,
    "poetry": {
        "gpu": None,
        "no-gpu": poetry_no_gpu,
    },
}


def build_dockerfile(
    manifest: Manifest, packager: Packager, gpu: bool, python_version: str
) -> str:
    """A function to build a dockerfile

    It delegates to the correct builder, based on the packager and gpu support


    Parameters
    ----------
    manifest : Manifest
        The manifest of the project
    packager : Packager
        The detected packager
    gpu : bool
        The detected gpu support
    python_version : str
        _description_

    Returns
    -------
    str
        The dockerfile

    Raises
    ------
    click.ClickException
        An exception if the packager is not supported
    """

    strategy = BUILDERS.get(packager, {})

    if not strategy:
        raise click.ClickException(
            f"Packager {packager} is not supported. Please create a issue on github and create your own Dockerfile for now."
        )

    builder = strategy.get(gpu and "gpu" or "no-gpu", None)

    if not builder:
        raise click.ClickException(
            f"Packager {packager} {gpu and 'with GPU Support'} is not supported. Please create a issue on github and create your own Dockerfile for now."
        )

    return builder(manifest, python_version)


def docker_file_wizard(manifest: Manifest, auto: bool = True) -> str:
    """A wizard to generate a dockerfile

    Parameters
    ----------
    manifest : Manifest
        The manifest of the project
    auto : bool, optional
        Should we autodefault prompts to true, by default True

    Returns
    -------
    str
        The dockerfile

    ------
    ImportError
        If toml is not installed
    """
    python_version = (
        f"{ sys.version_info.major}.{ sys.version_info.minor}.{ sys.version_info.micro}"
    )
    python_version = (
        python_version
        if auto
        else click.prompt(
            "Which python version to do you want to use?", default=python_version
        )
    )

    packager = None

    gpu = "gpu" in manifest.requirements

    # loading environment
    # check if running in conda
    conda_env = os.environ.get("CONDA_DEFAULT_ENV")
    if conda_env:
        click.echo(f"Found running in conda environment {conda_env}")

        packager = Packager.CONDA

    # Check if pyproject.toml exists
    if os.path.exists("pyproject.toml"):
        # Check if poetry is installed
        try:
            import toml
        except ImportError as e:
            raise ImportError("Please install toml to use this feature") from e

        # Check if poetry is used
        pyproject = toml.load("pyproject.toml")
        if "tool" in pyproject and "poetry" in pyproject["tool"]:
            click.echo("Found poetry project")
            do = True if auto else click.confirm("Do you want to use poetry?")
            if do:
                packager = Packager.POETRY

    if not packager:
        click.echo(
            "No advanced packager found. Considering using poetry "
            "with a pyproject.toml or conda with a environment.yml"
        )

        if os.path.exists("requirements.txt"):
            click.prompt("Found requirements.txt file in current directory. Using it.")

        packager = Packager.PIP

    if not click.confirm(
        f"Would you like to generate Template Dockerfile: Using {packager} with Python {python_version} {'and' if gpu else 'without'} GPU support"
    ):
        raise click.Abort("Aborted")

    dockfile = build_dockerfile(
        manifest, packager, gpu=gpu, python_version=python_version
    )

    return dockfile


def check_overwrite_dockerfile(ctx: Context, param: str, value: bool) -> bool:
    """A callback to check if the dockerfile should be overwritten

    Parameters
    ----------
    ctx : Context
        The context of the click command
    param : str
        The parameter name
    value : str
        The value of the parameter

    Returns
    -------
    bool
        Should we overwrite the dockerfile?
    """

    app_file = ctx.params["dockerfile"]
    if os.path.exists(app_file) and not value:
        should_overwrite = click.confirm(
            "Docker already exists. Do you want to overwrite?", abort=True
        )
        if should_overwrite:
            return True
        else:
            raise click.Abort()

    return value


@click.command()
@click.option("--dockerfile", help="The dockerfile to generate", default="Dockerfile")
@click.option(
    "--overwrite-dockerfile",
    "-o",
    help="Should we overwrite the existing Dockerfile?",
    is_flag=True,
    default=False,
    callback=check_overwrite_dockerfile,
)
@click.pass_context
def wizard(ctx: Context, dockerfile: str, overwrite_dockerfile: bool) -> None:
    """Runs the port wizard to generate a dockerfile to be used with port"""

    manifest = get_manifest(ctx)

    dockfile = docker_file_wizard(manifest)

    with open(dockerfile, "w") as file:
        file.write(dockfile)
