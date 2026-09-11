from importlib import import_module
from typing import Any, Callable
from arkitekt.app.app import App
import json
import os


def emit_machine_readable(kind: str, data: Any) -> None:
    """Print ``data`` as JSON wrapped in ``--START_<KIND>--``/``--END_<KIND>--``.

    The sentinels let consumers (e.g. ``plugin build``'s in-container inspection)
    extract the payload from otherwise noisy stdout. Every ``--machine-readable``
    command emits through this helper so the framing stays uniform.
    """
    print(f"--START_{kind}--" + json.dumps(data) + f"--END_{kind}--")


def import_builder(builder: str) -> Callable[..., App]:
    module_path, function_name = builder.rsplit(".", 1)
    module = import_module(module_path)
    function = getattr(module, function_name)
    return function


def build_relative_dir(*paths):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *paths)
