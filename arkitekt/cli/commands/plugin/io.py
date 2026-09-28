import datetime
import uuid
from arkitekt.utils import create_arkitekt_folder
import os
from typing import Any, Optional, List, Dict
from arkitekt.app.app import App

from .types import (
    DEFAULT_BUILD_COMMAND,
    LEGACY_BUILD_COMMANDS,
    Build,
    BuildsConfigFile,
    Flavour,
)
from arkitekt.app.spec import app_manifest
from arkitekt_spec import (
    AppImage,
    AppManifest,
    DeploymentsFile,
    DockerImage,
    Inspection,
    dump_deployments,
    load_deployments,
)

import yaml
import json
from arkitekt.cli.errors import cli_error


def get_flavours(base_dir: Optional[str] = None, select: Optional[str] = None) -> Dict[str, Flavour]:
    """Loads and validates all flavours from the .arkitekt/flavours directory."""
    arkitekt_folder = create_arkitekt_folder(base_dir=base_dir)
    flavours_folder = os.path.join(arkitekt_folder, "flavours")

    if not os.path.exists(flavours_folder):
        cli_error(
            "Could not find the flavours folder. Please run `arkitekt plugin init` first"
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
        except Exception as e:
            # Naming the error matters now that flavours carry more than paths:
            # "config.yaml is invalid" for a mistyped platform sends the reader
            # hunting through a file the CLI could just quote back at them.
            cli_error(f"Could not load flavour {dir_name} ({config_path}): {e}")

        if flavour.build_command in LEGACY_BUILD_COMMANDS:
            # Written by a single-arch CLI, not chosen: the same build, spelled
            # the way buildx wants it. Migrated in memory only — the user's file
            # is theirs, and `selector add` rewrites it soon enough.
            flavour.build_command = list(DEFAULT_BUILD_COMMAND)

        flavours[dir_name] = flavour

    return flavours


def get_builds(selected_run: Optional[str] = None, base_dir: Optional[str] = None) -> Dict[str, Build]:
    """Loads the builds.yaml file and returns a dictionary of builds keyed by build_id."""
    path = create_arkitekt_folder(base_dir=base_dir)
    config_file = os.path.join(path, "builds.yaml")

    if not os.path.exists(config_file):
        cli_error(
            "Could not find any builds. Please run `arkitekt plugin build` first"
        )

    with open(config_file, "r") as file:
        config = BuildsConfigFile(**yaml.safe_load(file))

    selected_run = selected_run or config.latest_build_run
    return {
        build.build_id: build
        for build in config.builds
        if build.build_run == selected_run
    }


def app_to_manifest(app: App[Any], target: str) -> AppManifest:
    """What a build says it packages: the App's identity, and the target that finds it.

    The target is recorded so the image is run (and inspected) on the same app
    it was built for, not on whatever the default target happens to find.
    """
    return app_manifest(app, entrypoint=target)


def generate_build(
    build_run: str,
    build_id: str,
    flavour_name: str,
    flavour: Flavour,
    manifest: AppManifest,
    inspection: Optional[Inspection],
    base_dir: Optional[str] = None,
    platforms: Optional[List[str]] = None,
) -> Build:
    """Generates a Build record and appends it to builds.yaml."""
    path = create_arkitekt_folder(base_dir=base_dir)
    config_file = os.path.join(path, "builds.yaml")

    build = Build(
        manifest=manifest,
        flavour=flavour_name,
        selectors=flavour.selectors,
        build_id=build_id,
        build_run=build_run,
        description=flavour.description,
        inspection=inspection,
        platforms=list(platforms if platforms is not None else flavour.platforms),
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


def get_deployments(base_dir: Optional[str] = None) -> DeploymentsFile:
    """Loads deployments.yaml; returns an empty file if it does not exist."""
    path = create_arkitekt_folder(base_dir=base_dir)
    config_file = os.path.join(path, "deployments.yaml")
    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            return load_deployments(file.read())
    return DeploymentsFile()


def generate_deployment(
    deployment_run: str,
    build: Build,
    image: str,
    base_dir: Optional[str] = None,
) -> AppImage:
    """Generates a deployment record from a build and appends it to deployments.yaml."""
    if build.inspection is None:
        cli_error(f"Build {build.build_id} was never inspected, so it cannot be deployed")

    path = create_arkitekt_folder(base_dir=base_dir)
    config_file = os.path.join(path, "deployments.yaml")

    # Aliased fields by alias: the name a type checker knows a pydantic field by.
    app_image = AppImage(
        appImageId=uuid.uuid4().hex,
        manifest=build.manifest,
        flavourName=build.flavour,
        selectors=build.selectors,
        inspection=build.inspection,
        image=DockerImage(imageString=image, buildAt=datetime.datetime.now()),
    )

    config = get_deployments(base_dir=base_dir)
    config.app_images.append(app_image)
    config.latest_app_image = app_image.app_image_id

    with open(config_file, "w") as file:
        file.write(dump_deployments(config))

    return app_image
