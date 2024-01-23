from .types import Requirement
from .utils import build_relative_dir
from typing import List
import os


def compile_scopes() -> List[str]:
    """Compile all available scopes"""
    return ["read", "write"]


def compile_requirements():
    """Compile all available requirements"""
    return [Requirement.GPU.value]


def compile_builders():
    return ["arkitekt.builders.easy", "arkitekt.builders.port"]


def compile_runtimes():
    return ["nvidia", "standard"]


def compile_schema_versions() -> List[str]:
    z = build_relative_dir("schemas")
    return [
        os.path.basename(f) for f in os.listdir(z) if os.path.isdir(os.path.join(z, f))
    ]


def compile_configs() -> List[str]:
    z = build_relative_dir("configs")
    return [
        os.path.basename(f) for f in os.listdir(z) if os.path.isdir(os.path.join(z, f))
    ]


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
    z = build_relative_dir("schemas")
    return [
        os.path.basename(f).split(".")[0]
        for f in os.listdir(z)
        if os.path.isfile(os.path.join(z, f))
    ]
