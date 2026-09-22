"""Finding a buildx builder that can build the platforms a flavour asks for.

Docker's default builder uses the ``docker`` driver, which builds one platform
and loads it into the daemon. A multi-platform build needs a ``docker-container``
builder, and cross-building a foreign architecture needs emulation registered on
the host. Neither is something this CLI can assume, and neither is something it
should make the user discover from a buildkit error.

So: ask the builder what it can do (``docker buildx inspect --bootstrap`` lists
the platforms its nodes report) and refuse early, naming the remedy *and* the
opt-out. Asking the builder rather than reading ``/proc/sys/fs/binfmt_misc`` is
what makes this correct on Docker Desktop and on a remote native builder node,
where the host kernel says nothing useful.
"""

import platform as _platform
import re
import subprocess
from collections.abc import Sequence
from typing import Any, Optional

from arkitekt.cli.errors import cli_error

#: The builder this CLI creates when the default one cannot build multi-platform.
ARKITEKT_BUILDER = "arkitekt"

#: ``platform.machine()`` is not a docker platform; this is the mapping for the
#: architectures Arkitekt runs on. Anything else falls through to the raw value,
#: which docker will reject with its own (clear) message.
_MACHINE_TO_ARCH = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
}


def host_platform() -> str:
    """The docker platform of the local daemon, e.g. ``linux/amd64``.

    The daemon is asked first: it, not this process, is what runs the build, and
    on a remote or virtualised daemon the two disagree.
    """
    try:
        result = subprocess.run(
            ["docker", "version", "-f", "{{.Server.Os}}/{{.Server.Arch}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        reported = result.stdout.strip()
        if "/" in reported:
            return reported
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    machine = _platform.machine().lower()
    return f"linux/{_MACHINE_TO_ARCH.get(machine, machine)}"


def _builder_exists(name: str) -> bool:
    """Whether a builder of this name is already configured."""
    result = subprocess.run(
        ["docker", "buildx", "inspect", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def builder_platforms(name: str) -> list[str]:
    """The platforms a builder reports, across all of its nodes.

    ``--bootstrap`` starts the builder if it is not running, because a stopped
    builder reports nothing and that would read as "cannot build arm64".
    """
    try:
        result = subprocess.run(
            ["docker", "buildx", "inspect", "--bootstrap", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        cli_error(
            f"Could not inspect the docker buildx builder '{name}':\n{e.stdout}"
        )

    platforms: list[str] = []
    for line in result.stdout.splitlines():
        match = re.match(r"\s*Platforms:\s*(.+)", line)
        if match:
            platforms.extend(p.strip() for p in match.group(1).split(",") if p.strip())
    return platforms


def _supports(reported: Sequence[str], wanted: str) -> bool:
    """Whether ``wanted`` is covered by what a builder reports.

    Builders list variants (``linux/amd64/v2``) next to the base platform, and a
    request for ``linux/arm64`` is satisfied by ``linux/arm64/v8``.
    """
    return any(r == wanted or r.startswith(wanted + "/") for r in reported)


def _create_builder(name: str) -> None:
    """Create the container-driver builder a multi-platform build needs."""
    result = subprocess.run(
        [
            "docker", "buildx", "create",
            "--name", name,
            "--driver", "docker-container",
            "--bootstrap",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        cli_error(
            f"Could not create the docker buildx builder '{name}':\n{result.stdout}\n"
            "A multi-platform build needs a builder with the docker-container driver. "
            "Build for this machine only with `arkitekt plugin init --overwrite --no-multi-arch`."
        )


def ensure_builder(platforms: Sequence[str], console: Any = None) -> Optional[str]:
    """The builder to pass as ``--builder`` for these platforms.

    Building only for the host is what docker does out of the box, so that path
    creates nothing and returns ``None``: opting out of multi-arch stays exactly
    as cheap as it was before multi-arch existed.

    Raises (via :func:`cli_error`) when a requested platform cannot be built
    here, naming both how to fix the machine and how to opt out.
    """
    wanted = list(dict.fromkeys(platforms))
    if len(wanted) <= 1 and (not wanted or wanted[0] == host_platform()):
        return None

    if not _builder_exists(ARKITEKT_BUILDER):
        if console:
            console.print(
                f"Creating the docker buildx builder [bold]{ARKITEKT_BUILDER}[/bold] "
                "(docker-container driver), which a multi-platform build needs."
            )
        _create_builder(ARKITEKT_BUILDER)

    reported = builder_platforms(ARKITEKT_BUILDER)
    missing = [p for p in wanted if not _supports(reported, p)]
    if missing:
        cli_error(
            "The docker builder cannot build "
            + ", ".join(missing)
            + f" (it offers {', '.join(reported) or 'nothing'}).\n"
            "Cross-building another architecture needs emulation on this host:\n"
            "    docker run --privileged --rm tonistiigi/binfmt --install all\n"
            "Or build for this machine only: `arkitekt plugin init --overwrite --no-multi-arch`, "
            "or edit `platforms:` in .arkitekt/flavours/<flavour>/config.yaml."
        )

    return ARKITEKT_BUILDER
