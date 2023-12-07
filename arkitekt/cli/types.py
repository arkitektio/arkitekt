from pydantic import BaseModel, Field, validator
import datetime
from typing import List, Optional
from enum import Enum
import semver
import uuid
from rekuest.api.schema import DefinitionInput


class Framework(str, Enum):
    """Do we support other frameworks?"""

    VANILLA = "vanilla"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"


class Requirement(str, Enum):
    """ """

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

    class Config:
        validate_assignment = True


class Deployment(BaseModel):
    """A deployment is a Release of a Build.
    It contains the build_id, the manifest, the builder, the definitions, the image and the deployed_at timestamp.



    """

    deployment_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="The unique identifier of the deployment",
    )
    manifest: Manifest = Field(description="The manifest of the app that was deployed")
    builder: str = Field(
        description="The builder that was used to build the app. CUrrently always port"
    )
    build_id: str = Field(
        description="The build_id of the build that was deployed. Is referenced in the build.yaml file."
    )
    definitions: List[DefinitionInput] = Field(
        description="Definitions of nodes that are contained in the app."
    )
    image: str = Field(
        description="The docker image that was built for this deployment"
    )
    deployed_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        description="The timestamp of the deployment",
    )


class DeploymentsConfigFile(BaseModel):
    """The ConfigFile is a pydantic model that represents the deployments.yaml file


    Parameters
    ----------
    BaseModel : _type_
        _description_
    """

    deployments: List[Deployment] = []
    latest_deployment: datetime.datetime = Field(default_factory=datetime.datetime.now)


class Build(BaseModel):
    manifest: Manifest
    build_id: str
    builder: str
    build_at: datetime.datetime = Field(default_factory=datetime.datetime.now)


class BuildsConfigFile(BaseModel):
    builds: List[Build] = Field(default_factory=list)
    latest_build: Optional[Build]
