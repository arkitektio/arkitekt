from importlib import import_module
from arkitekt.cli.types import Manifest
from arkitekt.utils import create_arkitekt_folder
from pydantic import BaseModel, Field
import os
from typing import List, Optional
import yaml
import json
import datetime


def import_deployer(builder):
    module_path, function_name = builder.rsplit(".", 1)
    module = import_module(module_path)
    function = getattr(module, function_name)
    return function


def generate_definitions(module_path: str = "hu"):
    from rekuest.definition.registry import get_default_definition_registry

    module_path = "hu"
    import_module(module_path)

    reg = get_default_definition_registry()
    return list(reg.definitions.keys())


def load_manifest() -> Optional[Manifest]:
    path = create_arkitekt_folder()
    config_file = os.path.join(path, "manifest.yaml")
    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            manifest = yaml.safe_load(file)
        return Manifest(**manifest)
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
