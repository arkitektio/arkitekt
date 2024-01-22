from pydantic import BaseModel, Field, validator
import datetime
from typing import List, Optional, Union, Literal
from enum import Enum
import semver
import uuid
from rekuest.api.schema import DefinitionInput
from string import Formatter
import os

ALLOWED_BUILDER_KEYS = [
    "tag",
    "dockerfile",
]


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


class SelectorType(str, Enum):
    RAM = "ram"
    CPU = "cpu"
    GPU = "gpu"
    LABEL = "label"


class BaseSelector(BaseModel):
    """A selector is a way to describe a flavours preference for a
    compute node. It contains the node_id, the selector and the flavour_id.
    """

    required: bool = True

    class Config:
        extra = "forbid"

    def build_docker_params(self) -> List[str]:
        """Builds the docker params for this selector

        Should return a list of strings that can be used as docker params
        If the selector is not required, it should return an empty list

        Returns
        -------
        List[str]
            The docker params for this selector
        """
        return []

    def build_arkitekt_params(self) -> List[str]:
        """Builds the arkitekt params for this selector

        Returns
        -------
        List[str]
            The docker params for this selector
        """
        return []


class RAMSelector(BaseSelector):
    """A selector is a way to describe a flavours preference for a
    compute node. It contains the node_id, the selector and the flavour_id.
    """

    type: Literal["ram"]
    min: int


class CPUSelector(BaseSelector):
    """A selector is a way to describe a flavours preference for a
    compute node. It contains the node_id, the selector and the flavour_id.
    """

    type: Literal["cpu"]
    min: int
    frequency: Optional[int] = None


class CudaSelector(BaseSelector):
    """A selector is a way to describe a flavours preference for a
    compute node. It contains the node_id, the selector and the flavour_id.
    """

    type: Literal["cuda"]
    frequency: Optional[int] = Field(default=None, description="The frequency in MHz")
    memory: Optional[int] = Field(default=None, description="The memory in MB")
    architecture: Optional[str] = Field(
        default=None, description="The architecture of the GPU"
    )
    compute_capability: str = Field(
        default="3.5", description="The minimum compute capability"
    )
    cuda_cores: Optional[int] = None
    cuda_version: str = Field(default="10.2", description="The minimum cuda version")

    def build_docker_params(self) -> List[str]:
        """Builds the docker params for this selector

        Should return a list of strings that can be used as docker params
        If the selector is not required, it should return an empty list

        Returns
        -------
        List[str]
            The docker params for this selector
        """
        return [
            "--gpus",
            "all",
        ]


class RocmSelector(BaseSelector):
    """A selector is a way to describe a flavours preference for a
    compute node. It contains the node_id, the selector and the flavour_id.
    """

    type: Literal["rocm"]
    min: int
    frequency: Optional[int] = None
    memory: Optional[int] = None
    architecture: Optional[str] = None
    compute_capability: Optional[str] = None
    cuda_cores: Optional[int] = None
    cuda_version: Optional[str] = None

    def build_docker_params(self) -> List[str]:
        """Builds the docker params for this selector"""

        return [
            "--device=/dev/kfd",
            "--device=/dev/dri",
            "--group-add",
            "video",
            "--cap-add=SYS_PTRACE",
            "--security-opt",
            "seccomp=unconfined",
        ]


class LabelSelector(BaseSelector):
    """A selector is a way to describe a flavours preference for a
    compute node. It contains the node_id, the selector and the flavour_id.
    """

    type: Literal["label"]
    key: str
    value: str


class ServiceSelector(BaseSelector):
    """A service selector is a way to describe a flavours preference for a
    service. It contains the service_id,
    """

    type: Literal["service"]


Selector = Union[
    RAMSelector, CPUSelector, CudaSelector, RocmSelector, LabelSelector, ServiceSelector
]


class Inspection(BaseModel):
    definitions: List[DefinitionInput]
    size: int


class Flavour(BaseModel):
    selectors: List[Selector]
    description: str = Field(default="")
    dockerfile: str = Field(default="Dockerfile")
    build_command: List[str] = Field(
        default_factory=lambda: [
            "docker",
            "build",
            "-t",
            "{tag}",
            "-f",
            "{dockerfile}",
            ".",
        ]
    )

    @validator("build_command", each_item=True, always=True)
    def check_valid_template_name(cls, v):
        """Checks that the template name is valid"""
        for literal_text, field_name, format_spec, conversion in Formatter().parse(v):
            if field_name is not None:
                assert (
                    field_name in ALLOWED_BUILDER_KEYS
                ), f"Invalid template key {field_name}. Allowed keys are {ALLOWED_BUILDER_KEYS}"

        return v

    def generate_build_command(self, tag: str, relative_dir: str):
        """Generates the build command for this flavour"""

        dockerfile = os.path.join(relative_dir, self.dockerfile)

        return [v.format(tag=tag, dockerfile=dockerfile) for v in self.build_command]

    def check_relative_paths(self, flavour_folder: str):
        """Checks that the paths are relative to the flavour folder"""

        dockerfile_path = os.path.join(flavour_folder, self.dockerfile)

        if not os.path.exists(dockerfile_path):
            raise Exception(
                f"Could not find Dockerfile {self.dockerfile} in flavour {flavour_folder}"
            )


class Deployment(BaseModel):
    """A deployment is a Release of a Build.
    It contains the build_id, the manifest, the builder, the definitions, the image and the deployed_at timestamp.



    """

    deployment_run: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="The unique identifier of the deployment run",
    )

    deployment_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="The unique identifier of the deployment",
    )
    manifest: Manifest = Field(description="The manifest of the app that was deployed")
    selectors: List[Selector] = Field(
        description="The selectors are used to place this image on the nodes",
        default_factory=list,
    )
    flavour: str = Field(
        description="The flavour that was used to build this deployment",
        default="vanilla",
    )
    build_id: str = Field(
        description="The build_id of the build that was deployed. Is referenced in the build.yaml file."
    )
    inspection: Optional[Inspection] = Field(
        description="The inspection of the build that was deployed"
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
    latest_deployment_run: Optional[str] = None


class Build(BaseModel):
    build_run: str
    build_id: str
    inspection: Optional[Inspection] = None
    description: str = Field(default="")
    selectors: List[Selector] = Field(default_factory=list)
    flavour: str = Field(default="vanilla")
    manifest: Manifest
    build_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    base_docker_command: List[str] = Field(
        default_factory=lambda: ["docker", "run", "-it", "--net", "host"]
    )
    base_arkitekt_command: List[str] = Field(
        default_factory=lambda: ["arkitekt", "run", "prod", "--headless"]
    )

    def build_docker_command(self) -> List[str]:
        """Builds the docker command for this build"""

        base_command = self.base_docker_command

        for selector in self.selectors:
            base_command = base_command + selector.build_docker_params()

        base_command = base_command + [self.build_id]

        return base_command

    def build_arkitekt_command(self, fakts_url: str):
        """Builds the arkitekt command for this build"""

        base_command = self.base_arkitekt_command

        for selector in self.selectors:
            base_command = base_command + selector.build_arkitekt_params()

        base_command = base_command + ["--url", fakts_url]

        return base_command


class BuildsConfigFile(BaseModel):
    builds: List[Build] = Field(default_factory=list)
    latest_build_run: Optional[str] = None
