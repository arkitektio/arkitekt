from importlib.metadata import version
from pydantic import BaseModel, ConfigDict, Field, field_validator
import datetime
from typing import List, Optional, Union, Literal, Dict
from enum import Enum
import semver
import uuid
from fakts_next.models import Requirement
from string import Formatter
import os


class Manifest(BaseModel):
    identifier: str
    version: str
    author: str
    logo: Optional[str] = None
    entrypoint: str
    scopes: List[str]
    package_manager: Literal["pip", "uv"] = "pip"
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    @field_validator("version", mode="before")
    def version_must_be_semver(cls, v) -> str:
        """Checks that the version is a valid semver version"""
        if isinstance(v, str):
            try:
                semver.VersionInfo.parse(v)
            except ValueError:
                raise ValueError("Version must be a valid semver version")
        return str(v)

    def to_console_string(self):
        return f"📦 {self.identifier} ({self.version}) by {self.author}"

    def to_builder_dict(self):
        return {
            "identifier": self.identifier,
            "version": self.version,
            "logo": self.logo,
            "scopes": self.scopes,
        }
