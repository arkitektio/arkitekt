from .utils import build_relative_dir
from typing import List
import os


def compile_scopes() -> List[str]:
    """Compile all available scopes"""
    return ["read", "write"]


def compile_dockerfiles() -> List[str]:
    z = build_relative_dir("dockerfiles")
    return [
        os.path.basename(f).replace(".dockerfile", "")
        for f in os.listdir(z)
        if os.path.isfile(os.path.join(z, f))
    ]


def compile_templates() -> List[str]:
    z = build_relative_dir("templates")
    return [
        os.path.basename(f).split(".")[0]
        for f in os.listdir(z)
        if os.path.isfile(os.path.join(z, f))
    ]


def compile_services() -> List[str]:
    """The services `--services` accepts: the ones `gen` can actually resolve.

    Derived from `SERVICE_PACKAGES`, which is what `gen` reads the SDL from. It
    used to be the filenames in a `schemas/` directory of checked-in snapshots
    that nothing ever opened, and the two had drifted in both directions --
    seven names accepted here could not be resolved, and five real services were
    rejected.
    """
    from arkitekt.cli.commands.app.gen.init import SERVICE_PACKAGES

    return sorted(SERVICE_PACKAGES)
