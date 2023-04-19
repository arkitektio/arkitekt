from importlib import import_module
from arkitekt.cli.types import Manifest, Packager
from arkitekt.utils import create_arkitekt_folder
from pydantic import BaseModel, Field
import sys
import rich_click as click
from enum import Enum

try:
    from rekuest.api.schema import DefinitionInput
    from rekuest.definition.registry import get_default_definition_registry
except ImportError as e:
    raise ImportError("Please install rekuest to use this feature") from e


import os
from typing import Dict, List, Optional
import yaml
import json
import datetime

from subprocess import check_call


def import_deployer(builder):
    module_path, function_name = builder.rsplit(".", 1)
    module = import_module(module_path)
    function = getattr(module, function_name)
    return function


def generate_definitions(module_path) -> List[DefinitionInput]:
    import_module(module_path)
    reg = get_default_definition_registry()
    return list(reg.definitions.keys())


class Build(BaseModel):
    manifest: Manifest
    build_id: str
    builder: str
    build_at: datetime.datetime = Field(default_factory=datetime.datetime.now)


class ConfigFile(BaseModel):
    builds: List[Build] = Field(default_factory=list)
    latest_build: Optional[Build]


PIP_NO_GPU = """
FROM jhnnsrs/vanilla_pip:latest

# setup conda virtual environment
COPY ./requirements.txt /tmp/requirements.txt
RUN pip install /tmp/requirements.yml

"""

PIP_GPU = """
FROM jhnnsrs/vanilla_pip:latest

# setup conda virtual environment
COPY ./requirements.txt /tmp/requirements.txt
RUN pip install /tmp/requirements.yml

"""


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


def build_dockerfile(packager: Packager, gpu: bool, python_version: str) -> str:
    if packager == Packager.CONDA:
        if gpu:
            return CONDA_GPU
        else:
            return CONDA_NO_GPU

    if packager == Packager.PIP:
        if gpu:
            return PIP_GPU
        else:
            return PIP_NO_GPU

    raise click.ClickException(
        f"Packager {packager} {gpu and 'with GPU Support'} is not supported. Please create a issue on github and create your own Dockerfile for now."
    )


class DockerFile(BaseModel):
    base: Optional[str] = None
    commands: List[str] = Field(default_factory=list)


def docker_file_wizard(manifest: Manifest, auto: bool = True):
    # get python version
    python_version = sys.version_info
    python_version = (
        f"{python_version.major}.{python_version.minor}.{python_version.micro}"
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
            "No advanced packager found. Considering using poetry with a pyproject.toml or conda with a environment.yml"
        )

        if os.path.exists("requirements.txt"):
            click.prompt("Found requirements.txt file in current directory. Using it.")

        packager = Packager.PIP

    if click.confirm(
        f"Would you like to generate Template Dockerfile: Using {packager} with Python {python_version} {'and' if gpu else 'without'} GPU support"
    ):
        dockfile = build_dockerfile(packager, gpu=gpu, python_version=python_version)
        with open("Dockerfile", "w") as file:
            file.write(dockfile)


def get_builds() -> Dict[str, Build]:
    path = create_arkitekt_folder()
    config_file = os.path.join(path, "builds.yaml")

    builds = {}

    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            config = ConfigFile(**yaml.safe_load(file))

            builds = {build.build_id: build for build in config.builds}
            builds["latest"] = config.latest_build
            return builds
    else:
        return {}


def generate_build(
    builder: str,
    build_id: str,
    manifest: Manifest,
) -> Build:
    path = create_arkitekt_folder()

    config_file = os.path.join(path, "builds.yaml")

    build = Build(
        manifest=manifest,
        builder=builder,
        build_id=build_id,
    )

    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            config = ConfigFile(**yaml.safe_load(file))
            config.builds.append(build)
            config.latest_build = build
    else:
        config = ConfigFile(builds=[build], latest_build=build)

    with open(config_file, "w") as file:
        yaml.safe_dump(
            json.loads(config.json(exclude_none=True, exclude_unset=True)),
            file,
            sort_keys=True,
        )
