from pydantic import BaseModel, Field, validator
import datetime
from typing import List, Optional
import os
import yaml
from arkitekt.utils import create_arkitekt_folder
import json
from enum import Enum
import semver


class Requirement(str, Enum):
    GPU = "gpu"


class Packager(str, Enum):
    CONDA = "conda"
    POETRY = "poetry"
    PIP = "pip"


class Manifest(BaseModel):
    identifier: str
    version: str
    author: str
    logo: Optional[str]
    entrypoint: str
    scopes: List[str]
    requirements: List[Requirement] = Field(default_factory=list)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

    @validator("version", pre=True)
    def version_must_be_semver(cls, v):
        if isinstance(v, str):
            try:
                semver.VersionInfo.parse(v)
            except ValueError:
                raise ValueError("Version must be a valid semver version")
        return str(v)

    def to_console_string(self):
        return f"📦 {self.identifier} ({self.version}) by {self.author}"

    class Config:
        validate_assignment = True


class PortBuild(BaseModel):
    capabilities: List[str]


def load_portbuild() -> Optional[PortBuild]:
    path = create_arkitekt_folder()
    config_file = os.path.join(path, "portbuild.yaml")
    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            manifest = yaml.safe_load(file)
        return Manifest(**manifest)
    return None


def write_portbuild(build: PortBuild):
    path = create_arkitekt_folder()
    config_file = os.path.join(path, "portbuild.yaml")

    with open(config_file, "w") as file:
        yaml.safe_dump(
            json.loads(build.json(exclude_none=True, exclude_unset=True)),
            file,
            sort_keys=True,
        )
