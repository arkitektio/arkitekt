import os
from importlib import import_module
from arkitekt.apps import App
from typing import Type


def build_relative_dir(*paths):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *paths)


def import_builder(builder: str) -> Type[App]:
    module_path, function_name = builder.rsplit(".", 1)
    module = import_module(module_path)
    function = getattr(module, function_name)
    return function
