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
    """ A deployment is a Release of a Build. 
    It contains the build_id, the manifest, the builder, the definitions, the image and the deployed_at timestamp.

    
    
    """
    deployment_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the deployment")
    manifest: Manifest = Field(description="The manifest of the app that was deployed")
    builder: str = Field(description="The builder that was used to build the app. CUrrently always port")
    build_id: str = Field(description="The build_id of the build that was deployed. Is referenced in the build.yaml file.")
    definitions: List[DefinitionInput] = Field(description="Definitions of nodes that are contained in the app.")
    image: str = Field(description="The docker image that was built for this deployment")
    deployed_at: datetime.datetime = Field(default_factory=datetime.datetime.now, description="The timestamp of the deployment")


class ConfigFile(BaseModel):
    """The ConfigFile is a pydantic model that represents the deployments.yaml file


    Parameters
    ----------
    BaseModel : _type_
        _description_
    """
    deployments: List[Deployment] = []
    latest_deployment: datetime.datetime = Field(default_factory=datetime.datetime.now)


class DockerFile(BaseModel):
    base: Optional[str] = None
    commands: List[str] = Field(default_factory=list)


def load_deployments() -> ConfigFile:
    """ Loads the deployments.yaml file and returns a ConfigFile object
    if it exists. If it does not exist, it returns an empty ConfigFile object."""
    path = create_arkitekt_folder()
    config_file = os.path.join(path, "deployments.yaml")
    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            return ConfigFile(**yaml.safe_load(file))
    else:
        return ConfigFile()


def check_if_manifest_already_deployed(manifest: Manifest):
    """Checks if a manifest has already been deployed. If it has, it raises a click.ClickException.

    Parameters
    ----------
    manifest : Manifest
        THe manifest to check

    Raises
    ------
    click.ClickException
        A click exception if the manifest has already been deployed
    """
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
    """Generates a deployment from a build and an image
    
    Parameters
    ----------

    build : Build
        The build that should be deployed
    image: str
        The image that is the actuall deployment of the build
    with_definitions: bool:
        Should we generated and inspect definitions to bundle with
        the deployment?
    
    Returns:
    ------
    Deployment: The created deployment
    
    """


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
