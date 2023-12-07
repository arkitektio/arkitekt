from arkitekt.utils import create_arkitekt_folder
import os
from typing import Optional
from arkitekt.cli.types import (
    Manifest,
    Build,
    BuildsConfigFile,
    Deployment,
    DeploymentsConfigFile,
)
import yaml
import json
from typing import Dict
import datetime


def load_manifest_yaml(path: str) -> Manifest:
    """Loads a manifest from a yaml file

    Uses yaml safe load to load the manifest from a yaml file
    (to avoid unsafe yaml attributes)

    Parameters
    ----------
    path : str
        The path to the yaml file

    Returns
    -------
    Manifest
        The loaded manifest
    """
    with open(path, "r") as file:
        manifest = yaml.safe_load(file)
        return Manifest(**manifest)


def load_manifest() -> Optional[Manifest]:
    """Loads the manifest from the arkitekt folder

    Will load the manifest from the current working directories
    arkitekt folder. If no folder exists, it will create one, but
    will not create a manifest.

    Returns
    -------
    Optional[Manifest]
        The loaded manifest, or None if no manifest exists
    """
    path = create_arkitekt_folder()
    config_file = os.path.join(path, "manifest.yaml")
    if os.path.exists(config_file):
        return load_manifest_yaml(config_file)
    return None


def write_manifest(manifest: Manifest):
    """Writes a manifest to the arkitekt folder

    Will write a manifest to the current working directories
    arkitekt folder. If no folder exists, it will create one.


    Parameters
    ----------
    manifest : Manifest
        The manifest to write
    """
    path = create_arkitekt_folder()
    config_file = os.path.join(path, "manifest.yaml")

    with open(config_file, "w") as file:
        yaml.safe_dump(
            json.loads(manifest.json(exclude_none=True, exclude_unset=True)),
            file,
            sort_keys=True,
        )


def get_builds() -> Dict[str, Build]:
    """Will load the builds.yaml file and return a dictionary of builds

    Will load the builds.yaml file and return a dictionary of builds
    where the key is the build_id and the value is the build object.


    Returns
    -------
    Dict[str, Build]
        The loaded builds
    """
    path = create_arkitekt_folder()
    config_file = os.path.join(path, "builds.yaml")

    builds = {}

    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            config = BuildsConfigFile(**yaml.safe_load(file))

            builds = {build.build_id: build for build in config.builds}
            if config.latest_build:
                builds["latest"] = config.latest_build
            return builds
    else:
        return {}


def generate_build(
    builder: str,
    build_id: str,
    manifest: Manifest,
) -> Build:
    """Generates a build from a builder, build_id and manifest

    Will generate a build from a builder, build_id and manifest,
    and write it to the builds.yaml file in the arkitekt folder.


    Parameters
    ----------
    builder : str
        The builder that was used to build the build
    build_id : str
        The build_id of the build
    manifest : Manifest
        The manifest of the build

    Returns
    -------
    Build
        The generated build
    """
    path = create_arkitekt_folder()

    config_file = os.path.join(path, "builds.yaml")

    build = Build(
        manifest=manifest,
        builder=builder,
        build_id=build_id,
    )

    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            config = BuildsConfigFile(**yaml.safe_load(file))
            config.builds.append(build)
            config.latest_build = build
    else:
        config = BuildsConfigFile(builds=[build], latest_build=build)

    with open(config_file, "w") as file:
        yaml.safe_dump(
            json.loads(config.json(exclude_none=True, exclude_unset=True)),
            file,
            sort_keys=True,
        )

    return build


def get_deployments() -> DeploymentsConfigFile:
    """Loads the deployments.yaml file and returns the deployments

    Will load the deployments.yaml file and return the deployments
    as a DeploymentsConfigFile object. If no deployments.yaml file
    exists, it will return an empty DeploymentsConfigFile object.

    Returns
    -------
    DeploymentsConfigFile
        The deployments as a DeploymentsConfigFile object
    """
    path = create_arkitekt_folder()
    config_file = os.path.join(path, "deployments.yaml")
    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            return DeploymentsConfigFile(**yaml.safe_load(file))
    else:
        return DeploymentsConfigFile()


def generate_deployment(
    build: Build,
    image: str,
    with_definitions: bool =True,
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

    deployment = Deployment(
        build_id=build.build_id,
        manifest=build.manifest,
        builder=build.builder,
        definitions=[],
        image=image,
    )

    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            config = DeploymentsConfigFile(**yaml.safe_load(file))
            config.deployments.append(deployment)
            config.latest_deployment = datetime.datetime.now()
    else:
        config = DeploymentsConfigFile(deployments=[deployment])
        config.latest_deployment = datetime.datetime.now()

    with open(config_file, "w") as file:
        yaml.safe_dump(
            json.loads(config.json(exclude_none=True)),
            file,
            sort_keys=True,
        )

    return deployment
