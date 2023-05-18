from typing import Dict, List, Optional, Union, Callable, Coroutine, Type
from rekuest.api.schema import WidgetInput, PortGroupInput
from rekuest.definition.registry import get_default_definition_registry
from rekuest.structures.registry import StructureRegistry
from rekuest.structures.default import get_default_structure_registry
from rekuest.actors.types import Actifier
import os
from functools import wraps


def create_arkitekt_folder(with_cache: bool = True):
    """Create the arkitekt folder"""
    os.makedirs(".arkitekt", exist_ok=True)
    if with_cache:
        os.makedirs(".arkitekt/cache", exist_ok=True)

    gitignore = os.path.join(".arkitekt", ".gitignore")
    dockerignore = os.path.join(".arkitekt", ".dockerignore")
    if not os.path.exists(gitignore):
        with open(gitignore, "w") as f:
            f.write(
                "# Hiding Arkitekt Credential files from git\n*.json\n*.temp\ncache/"
            )
    if not os.path.exists(dockerignore):
        with open(dockerignore, "w") as f:
            f.write(
                "# Hiding Arkitekt Credential files from git\n*.json\n*.temp\ncache/"
            )

    return ".arkitekt"
