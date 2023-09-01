from importlib import import_module
from arkitekt.cli.types import Manifest
from arkitekt.cli.build import Build
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
from typing import List, Optional
import yaml
import json
import datetime
import uuid
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


class Deployment(BaseModel):
    deployment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    manifest: Manifest
    builder: str
    build_id: str
    definitions: List[DefinitionInput]
    image: str
    deployed_at: datetime.datetime = Field(default_factory=datetime.datetime.now)


class ConfigFile(BaseModel):
    deployments: List[Deployment] = []
    latest_deployment: datetime.datetime = Field(default_factory=datetime.datetime.now)


class DockerFile(BaseModel):
    base: Optional[str] = None
    commands: List[str] = Field(default_factory=list)


def load_deployments() -> ConfigFile:
    path = create_arkitekt_folder()
    config_file = os.path.join(path, "deployments.yaml")
    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            return ConfigFile(**yaml.safe_load(file))
    else:
        return ConfigFile()


def check_if_manifest_already_deployed(manifest: Manifest):
    config = load_deployments()
    for deployment in config.deployments:
        if (
            deployment.manifest.identifier == manifest.identifier
            and deployment.manifest.version == manifest.version
        ):
            raise click.ClickException(
                f"Deployment of {manifest.identifier}/{manifest.version} already exists. You cannot deploy the same version twice."
            )


def generate_deployment(
    build: Build,
    image: str,
    with_definitions=True,
) -> Deployment:
    path = create_arkitekt_folder()

    config_file = os.path.join(path, "deployments.yaml")

    definitions = generate_definitions("app") if with_definitions else []

    deployment = Deployment(
        build_id=build.build_id,
        manifest=build.manifest,
        builder=build.builder,
        definitions=definitions,
        image=image,
    )

    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            config = ConfigFile(**yaml.safe_load(file))
            config.deployments.append(deployment)
            config.latest_deployment = datetime.datetime.now()
    else:
        config = ConfigFile(deployments=[deployment])
        config.latest_deployment = datetime.datetime.now()

    with open(config_file, "w") as file:
        yaml.safe_dump(
            json.loads(config.json(exclude_none=True)),
            file,
            sort_keys=True,
        )
