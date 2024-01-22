from importlib import import_module
from typing import Callable
from arkitekt.apps.types import App
import os


def import_builder(builder: str) -> Callable[..., App]:
    module_path, function_name = builder.rsplit(".", 1)
    module = import_module(module_path)
    function = getattr(module, function_name)
    return function


def build_relative_dir(*paths):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *paths)
