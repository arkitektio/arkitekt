import datetime
import uuid
from arkitekt.utils import create_arkitekt_folder
import os
from typing import NoReturn

from .types import (
    DEFAULT_BUILD_COMMAND,
    LEGACY_BUILD_COMMANDS,
    Build,
    BuildsConfigFile,
    Flavour,
)
from arkitekt_spec import (
    AppImage,
    AppManifest,
    DeploymentsFile,
    DockerImage,
    Inspection,
    current_spec_version,
    dump_deployments,
    load_deployments,
)

import yaml
import json
from pydantic import ValidationError
from arkitekt.cli.errors import cli_error
from arkitekt.cli.ui import command_hint


def get_flavours(base_dir: str | None = None, select: str | None = None) -> dict[str, Flavour]:
    """Loads and validates all flavours from the .arkitekt/flavours directory."""
    arkitekt_folder = create_arkitekt_folder(base_dir=base_dir)
    flavours_folder = os.path.join(arkitekt_folder, "flavours")

    if not os.path.exists(flavours_folder):
        cli_error(
            f"Could not find the flavours folder. Add one first: `{command_hint('plugin flavour add', base_dir)}`"
        )

    flavours: dict[str, Flavour] = {}

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


def _unreadable(config_file: str, error: ValidationError) -> NoReturn:
    """A file this CLI refuses, which is usually one written before files named their spec."""
    cli_error(
        f"Could not read {config_file}. If it was written by an older arkitekt, which named no "
        # The file is in the project's .arkitekt folder: the project is the one above it.
        f"spec version, delete it: `{command_hint('plugin build', os.path.dirname(os.path.dirname(config_file)))}` "
        f"writes a new one.\n\n{error}"
    )


def _read_builds(config_file: str) -> BuildsConfigFile:
    with open(config_file) as file:
        try:
            return BuildsConfigFile(**yaml.safe_load(file))
        except ValidationError as error:
            _unreadable(config_file, error)


def get_builds(selected_run: str | None = None, base_dir: str | None = None) -> dict[str, Build]:
    """Loads the builds.yaml file and returns a dictionary of builds keyed by build_id."""
    path = create_arkitekt_folder(base_dir=base_dir)
    config_file = os.path.join(path, "builds.yaml")

    if not os.path.exists(config_file):
        cli_error(
            f"Could not find any builds. Build one first: `{command_hint('plugin build', base_dir)}`"
        )

    config = _read_builds(config_file)

    selected_run = selected_run or config.latest_build_run
    return {
        build.build_id: build
        for build in config.builds
        if build.build_run == selected_run
    }


def generate_build(
    build_run: str,
    build_id: str,
    flavour_name: str,
    flavour: Flavour,
    manifest: AppManifest,
    inspection: Inspection | None,
    base_dir: str | None = None,
    platforms: list[str] | None = None,
) -> Build:
    """Generates a Build record and appends it to builds.yaml."""
    path = create_arkitekt_folder(base_dir=base_dir)
    config_file = os.path.join(path, "builds.yaml")

    build = Build(
        manifest=manifest,
        flavour=flavour_name,
        selectors=flavour.selectors,
        capabilities=flavour.capabilities,
        build_id=build_id,
        build_run=build_run,
        description=flavour.description,
        inspection=inspection,
        platforms=list(platforms if platforms is not None else flavour.platforms),
    )

    if os.path.exists(config_file):
        config = _read_builds(config_file)
        config.builds.append(build)
        config.latest_build_run = build_run
        config.spec_version = current_spec_version()
    else:
        config = BuildsConfigFile(
            spec_version=current_spec_version(), builds=[build], latest_build_run=build_run
        )

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


def get_deployments(base_dir: str | None = None) -> DeploymentsFile:
    """Loads deployments.yaml; returns an empty file if it does not exist."""
    path = create_arkitekt_folder(base_dir=base_dir)
    config_file = os.path.join(path, "deployments.yaml")
    if os.path.exists(config_file):
        with open(config_file) as file:
            try:
                return load_deployments(file.read())
            except ValidationError as error:
                _unreadable(config_file, error)
    return DeploymentsFile(spec_version=current_spec_version())


def generate_deployment(
    deployment_run: str,
    build: Build,
    image: str,
    base_dir: str | None = None,
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
        capabilities=build.capabilities,
        inspection=build.inspection,
        image=DockerImage(imageString=image, buildAt=datetime.datetime.now()),
    )

    config = get_deployments(base_dir=base_dir)
    config.app_images.append(app_image)
    config.latest_app_image = app_image.app_image_id
    config.spec_version = current_spec_version()

    with open(config_file, "w") as file:
        file.write(dump_deployments(config))

    return app_image
