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
    with open(path, "r") as file:
        manifest = yaml.safe_load(file)
        return Manifest(**manifest)


def load_manifest() -> Optional[Manifest]:
    path = create_arkitekt_folder()
    config_file = os.path.join(path, "manifest.yaml")
    if os.path.exists(config_file):
        return load_manifest_yaml(config_file)
    return None


def write_manifest(manifest: Manifest):
    path = create_arkitekt_folder()
    config_file = os.path.join(path, "manifest.yaml")

    with open(config_file, "w") as file:
        yaml.safe_dump(
            json.loads(manifest.json(exclude_none=True, exclude_unset=True)),
            file,
            sort_keys=True,
        )


def get_builds() -> Dict[str, Build]:
    path = create_arkitekt_folder()
    config_file = os.path.join(path, "builds.yaml")

    builds = {}

    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            config = BuildsConfigFile(**yaml.safe_load(file))

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


def get_deployments() -> DeploymentsConfigFile:
    """Loads the deployments.yaml file and returns a ConfigFile object
    if it exists. If it does not exist, it returns an empty ConfigFile object."""
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

    definitions = []

    deployment = Deployment(
        build_id=build.build_id,
        manifest=build.manifest,
        builder=build.builder,
        definitions=definitions,
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
