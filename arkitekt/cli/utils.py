import os
from importlib import import_module
from arkitekt.apps import App
from typing import Type


def build_relative_dir(*paths):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *paths)
