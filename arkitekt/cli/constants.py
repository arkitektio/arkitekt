from .utils import build_relative_dir
from typing import List
import os


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

