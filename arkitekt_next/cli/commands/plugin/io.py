import datetime
import uuid
from arkitekt_next.utils import create_arkitekt_next_folder
import os
from typing import Optional, List, Dict
from arkitekt_next.cli.types import (
    Manifest,
)

from .types import (
    Build,
    BuildsConfigFile,
    Flavour,
    DeploymentsConfigFile,
)
from kabinet.api.schema import (
    InspectionInput,
    AppImageInput,
    DockerImageInput,
    ManifestInput,
)

import yaml
import json
from arkitekt_next.cli.errors import cli_error


def get_flavours(base_dir: Optional[str] = None, select: Optional[str] = None) -> Dict[str, Flavour]:
    """Loads and validates all flavours from the .arkitekt_next/flavours directory."""
    arkitekt_next_folder = create_arkitekt_next_folder(base_dir=base_dir)
    flavours_folder = os.path.join(arkitekt_next_folder, "flavours")

    if not os.path.exists(flavours_folder):
        cli_error(
            "Could not find the flavours folder. Please run `arkitekt-next plugin init` first"
        )

    flavours: Dict[str, Flavour] = {}

    for dir_name in os.listdir(flavours_folder):
        dir_path = os.path.join(flavours_folder, dir_name)
        if not os.path.isdir(dir_path):
            continue
        if select is not None and select != dir_name:
            continue

        config_path = os.path.join(dir_path, "config.yaml")
        if not os.path.exists(config_path):
            cli_error(
                f"Flavour {dir_name} is invalid: no config.yaml found"
            )

        with open(config_path) as f:
            valued = yaml.load(f, Loader=yaml.SafeLoader)
        try:
            flavour = Flavour.model_validate(valued)
            flavour.check_relative_paths(dir_path)
            flavours[dir_name] = flavour
        except Exception as e:
            cli_error(
                f"Could not load flavour {dir_name}: config.yaml is invalid"
            )

    return flavours


def get_builds(selected_run: Optional[str] = None, base_dir: Optional[str] = None) -> Dict[str, Build]:
    """Loads the builds.yaml file and returns a dictionary of builds keyed by build_id."""
    path = create_arkitekt_next_folder(base_dir=base_dir)
    config_file = os.path.join(path, "builds.yaml")

    if not os.path.exists(config_file):
        cli_error(
            "Could not find any builds. Please run `arkitekt-next app kabinet build` first"
        )

    with open(config_file, "r") as file:
        config = BuildsConfigFile(**yaml.safe_load(file))

    selected_run = selected_run or config.latest_build_run
    return {
        build.build_id: build
        for build in config.builds
        if build.build_run == selected_run
    }


def manifest_to_input(manifest: Manifest) -> ManifestInput:
    return ManifestInput(
        identifier=manifest.identifier,
        version=manifest.version,
        author=manifest.author,
        logo=manifest.logo,
        scopes=tuple(manifest.scopes),
    )


def generate_build(
    build_run: str,
    build_id: str,
    flavour_name: str,
    flavour: Flavour,
    manifest: Manifest,
    inspection: Optional[InspectionInput],
    base_dir: Optional[str] = None,
) -> Build:
    """Generates a Build record and appends it to builds.yaml."""
    path = create_arkitekt_next_folder(base_dir=base_dir)
    config_file = os.path.join(path, "builds.yaml")

    build = Build(
        manifest=manifest_to_input(manifest),
        flavour=flavour_name,
        selectors=flavour.selectors,
        build_id=build_id,
        build_run=build_run,
        description=flavour.description,
        inspection=inspection,
    )

    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            config = BuildsConfigFile(**yaml.safe_load(file))
            config.builds.append(build)
            config.latest_build_run = build_run
    else:
        config = BuildsConfigFile(builds=[build], latest_build_run=build_run)

    with open(config_file, "w") as file:
        yaml.safe_dump(
            json.loads(
                config.model_dump_json(
                    exclude_none=True, exclude_unset=True, by_alias=True
                )
            ),
            file,
            sort_keys=True,
        )

    return build


def get_deployments(base_dir: Optional[str] = None) -> DeploymentsConfigFile:
    """Loads deployments.yaml; returns an empty config if the file does not exist."""
    path = create_arkitekt_next_folder(base_dir=base_dir)
    config_file = os.path.join(path, "deployments.yaml")
    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            return DeploymentsConfigFile(**yaml.safe_load(file))
    return DeploymentsConfigFile()


def generate_deployment(
    deployment_run: str,
    build: Build,
    image: str,
    base_dir: Optional[str] = None,
) -> AppImageInput:
    """Generates a deployment record from a build and appends it to deployments.yaml."""
    path = create_arkitekt_next_folder(base_dir=base_dir)
    config_file = os.path.join(path, "deployments.yaml")

    app_image = AppImageInput(
        appImageId=uuid.uuid4().hex,
        manifest=build.manifest,
        flavourName=build.flavour,
        selectors=build.selectors,
        inspection=build.inspection,
        image=DockerImageInput(imageString=image, buildAt=datetime.datetime.now()),
    )

    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            config = DeploymentsConfigFile(**yaml.safe_load(file))
            config.app_images.append(app_image)
            config.latest_app_image = app_image.app_image_id
    else:
        config = DeploymentsConfigFile(
            app_images=[app_image], latest_app_image=app_image.app_image_id
        )

    with open(config_file, "w") as file:
        yaml.safe_dump(
            json.loads(config.model_dump_json(exclude_none=True, by_alias=True)),
            file,
            sort_keys=True,
        )

    return app_image
