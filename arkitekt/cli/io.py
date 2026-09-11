import datetime
import uuid
from arkitekt.utils import create_arkitekt_folder
import os
from typing import Optional, List, Dict
from arkitekt.cli.types import (
    Manifest,
)
import yaml
import json


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


def load_manifest(base_dir: Optional[str] = None) -> Optional[Manifest]:
    """Loads the manifest from the arkitekt folder

    Will load the manifest from the given directory's arkitekt folder
    (defaults to cwd). If no folder exists, it will create one, but
    will not create a manifest.

    Parameters
    ----------
    base_dir : str, optional
        Base directory to look for the manifest in. Defaults to os.getcwd().

    Returns
    -------
    Optional[Manifest]
        The loaded manifest, or None if no manifest exists
    """
    path = create_arkitekt_folder(base_dir=base_dir)
    config_file = os.path.join(path, "manifest.yaml")
    if os.path.exists(config_file):
        return load_manifest_yaml(config_file)
    return None


def write_manifest(manifest: Manifest, base_dir: Optional[str] = None):
    """Writes a manifest to the arkitekt folder

    Will write a manifest to the given directory's arkitekt folder
    (defaults to cwd). If no folder exists, it will create one.

    Parameters
    ----------
    manifest : Manifest
        The manifest to write
    base_dir : str, optional
        Base directory to write the manifest to. Defaults to os.getcwd().
    """
    path = create_arkitekt_folder(base_dir=base_dir)
    config_file = os.path.join(path, "manifest.yaml")

    with open(config_file, "w") as file:
        yaml.safe_dump(
            manifest.model_dump(mode="json", exclude_none=True, exclude_unset=True),
            file,
            sort_keys=True,
        )
