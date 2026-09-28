from pydantic import BaseModel, Field, field_validator
import datetime
from typing import List, Optional


from string import Formatter
import os
import shlex

from arkitekt_spec import AppManifest, Inspection, Selector

ALLOWED_BUILDER_KEYS = [
    "tag",
    "dockerfile",
    "package_version",
    "platform",
    "output",
]

#: What a flavour builds for unless it says otherwise: the two architectures an
#: Arkitekt node is actually deployed on. A single-platform list is the opt-out
#: (``arkitekt plugin init --no-multi-arch``).
DEFAULT_PLATFORMS = ["linux/amd64", "linux/arm64"]

#: The build command every flavour gets today. ``{platform}`` and ``{output}``
#: are filled per pass: the host platform is ``--load``ed so it can be inspected
#: and staged, the rest are built to cache and pushed as one manifest list.
DEFAULT_BUILD_COMMAND = [
    "docker",
    "buildx",
    "build",
    "--platform",
    "{platform}",
    "{output}",
    "-t",
    "{tag}",
    "-f",
    "{dockerfile}",
    ".",
]

#: Build commands written by an older CLI. A flavour still carrying one is not
#: customised — it is just spelled the way the single-arch CLI spelled it — so it
#: is migrated to :data:`DEFAULT_BUILD_COMMAND` on load rather than treated as a
#: user's own command (see ``io.get_flavours``).
LEGACY_BUILD_COMMANDS = (
    ["docker", "build", "-t", "{tag}", "-f", "{dockerfile}", "."],
)


class Flavour(BaseModel):
    """ Flavour is a pydantic model that represents a flavour of an app image"""
    selectors: List[Selector]
    description: str = Field(default="")
    dockerfile: str = Field(default="Dockerfile")
    platforms: List[str] = Field(default_factory=lambda: list(DEFAULT_PLATFORMS))
    build_command: List[str] = Field(default_factory=lambda: list(DEFAULT_BUILD_COMMAND))

    @field_validator("build_command", mode="before")
    def check_valid_template_name(cls, value):
        """Checks that the build_command templates are valid"""

        for v in value:
            for literal_text, field_name, format_spec, conversion in Formatter().parse(
                v
            ):
                if field_name is not None:
                    assert (
                        field_name in ALLOWED_BUILDER_KEYS
                    ), f"Invalid template key {field_name}. Allowed keys are {ALLOWED_BUILDER_KEYS}"

        return value

    def is_customized(self) -> bool:
        """Whether someone edited ``build_command`` instead of taking the default.

        A customised command is run verbatim, which means this CLI cannot place
        the platform and output flags in it — so such a flavour builds for one
        platform only.
        """
        return self.build_command not in (
            DEFAULT_BUILD_COMMAND,
            *LEGACY_BUILD_COMMANDS,
        )

    def generate_build_command(
        self,
        tag: str,
        relative_dir: str,
        platform: str = "",
        output: str = "",
        builder: Optional[str] = None,
    ) -> List[str]:
        """Generates the build command for this flavour.

        ``platform`` is a comma-joined docker platform list and ``output`` a
        buildx ``--load``/``--push``/``--output ...`` fragment; a customised
        command names neither, and simply never has them rendered into it.

        The builder is passed in, not stored: which builder can do a
        multi-platform build is a property of the machine, not of the flavour.
        """

        dockerfile = os.path.join(relative_dir, self.dockerfile)

        rendered = [
            v.format(tag=tag, dockerfile=dockerfile, platform=platform, output=output)
            for v in self.build_command
        ]
        # ``{output}`` renders empty for a plain cache pass; an empty argument
        # would reach docker as "" and be read as the build context.
        rendered = [v for v in rendered if v != ""]

        if builder and rendered[:3] == ["docker", "buildx", "build"]:
            rendered = rendered[:3] + ["--builder", builder] + rendered[3:]

        return rendered

    def check_relative_paths(self, flavour_folder: str):
        """Checks that the paths are relative to the flavour folder"""

        dockerfile_path = os.path.join(flavour_folder, self.dockerfile)

        if not os.path.exists(dockerfile_path):
            raise Exception(
                f"Could not find Dockerfile {self.dockerfile} in flavour {flavour_folder}"
            )


class Build(BaseModel):
    build_run: str
    build_id: str
    inspection: Optional[Inspection] = None
    description: str = Field(default="")
    selectors: List[Selector] = Field(default_factory=list)
    flavour: str = Field(default="vanilla")
    #: The platforms this build compiled. Only the host one was loaded locally;
    #: publish pushes the whole list as a manifest list. Empty in a builds.yaml
    #: written before multi-arch existed, which is the single-arch record it was.
    platforms: List[str] = Field(default_factory=list)
    manifest: AppManifest
    build_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    base_docker_command: List[str] = Field(
        default_factory=lambda: ["docker", "run", "-it", "--net", "host"]
    )
    base_arkitekt_command: List[str] = Field(
        default_factory=lambda: ["arkitekt", "run", "prod", "--headless"]
    )

    def build_docker_command(self) -> List[str]:
        """Builds the docker command for this build.

        Mirrors the deployer's selector mapping: a cuda selector requests the
        GPUs; every other kind constrains placement, not the run command.
        (These used to call a ``selector.build_docker_params()`` that never
        existed, so any flavour with a selector raised AttributeError.)
        """

        base_command = list(self.base_docker_command)

        if any(selector.kind == "cuda" for selector in self.selectors):
            base_command = base_command + ["--gpus", "all"]

        base_command = base_command + [self.build_id]

        return base_command

    def build_arkitekt_command(self, fakts_url: str):
        """Builds the arkitekt command for this build.

        The target recorded at build time is passed on, so the container runs the
        app the image was built for.
        """

        base_command = list(self.base_arkitekt_command)
        if self.manifest.entrypoint:
            base_command = base_command + [shlex.quote(self.manifest.entrypoint)]

        base_command = base_command + ["--url", fakts_url]

        return base_command


class BuildsConfigFile(BaseModel):
    builds: List[Build] = Field(default_factory=list)
    latest_build_run: Optional[str] = None
