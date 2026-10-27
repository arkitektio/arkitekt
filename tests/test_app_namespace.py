"""An app's own enums, memory structures and models are in its namespace; a library's are not.

The same app gets the same identifiers whether its file is run (``__main__``) or
imported, and a type from a library (a fixture package outside the app, numpy)
keeps the identifier of its module in every app: port matching compares
identifiers, so a library type namespaced per app would never match across apps.
"""

import importlib
import runpy
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path

import numpy as np
import pytest

from arkitekt import App

LIBRARY = '''
from enum import Enum


class ProjectionMode(Enum):
    MAX = "max"
    MEAN = "mean"
'''

APP = '''
from enum import Enum

import numpy as np
from sharedlib.schema import ProjectionMode

from arkitekt import App


class ThresholdMethod(Enum):
    OTSU = "otsu"
    LI = "li"


class Blob:
    pass


app = App("{identifier}")
app.memory_structure(Blob)
app.memory_structure(np.ndarray)


@app.model
class Settings:
    sigma: float = 1.0


def segment(
    method: ThresholdMethod, mode: ProjectionMode, settings: Settings, image: np.ndarray
) -> Blob:
    """Segment"""
    return Blob()


app.register_action(segment)
'''


@pytest.fixture
def files(tmp_path: Path) -> Iterator[Path]:
    """A library package and two apps in separate directories, undone afterwards."""
    path, modules = list(sys.path), set(sys.modules)
    (tmp_path / "lib" / "sharedlib").mkdir(parents=True)
    _ = (tmp_path / "lib" / "sharedlib" / "__init__.py").write_text("")
    _ = (tmp_path / "lib" / "sharedlib" / "schema.py").write_text(LIBRARY)
    for directory, name, identifier in (
        ("apps", "cluster_segment_path_app", "cluster-segment-path"),
        ("other", "random_image_app", "random-image-generator"),
    ):
        (tmp_path / directory).mkdir()
        _ = (tmp_path / directory / f"{name}.py").write_text(APP.format(identifier=identifier))
    sys.path.insert(0, str(tmp_path / "lib"))
    yield tmp_path
    sys.path[:] = path
    for name in set(sys.modules) - modules:
        del sys.modules[name]


def identifiers(module: Mapping[str, object]) -> dict[str, str]:
    """The identifier of every port of the ``segment`` of the module's ``app``, by port key."""
    app = module["app"]
    assert isinstance(app, App)
    definition = app.registry.implementations["segment"].definition
    return {port.key: str(port.identifier) for port in (*definition.args, *definition.returns)}


def test_an_app_gets_the_same_identifiers_run_or_imported(files: Path) -> None:
    script = files / "apps" / "cluster_segment_path_app.py"
    as_main = identifiers(runpy.run_path(str(script), run_name="__main__"))
    sys.path.insert(0, str(script.parent))
    as_import = identifiers(vars(importlib.import_module("cluster_segment_path_app")))

    assert as_main == as_import == {
        "method": "@cluster-segment-path/thresholdmethod",
        "mode": "@sharedlib.schema/projectionmode",
        "settings": "@cluster-segment-path/settings",
        "image": "@numpy/ndarray",
        "return0": "@cluster-segment-path/blob",
    }


def test_a_library_type_is_the_same_in_two_apps(files: Path) -> None:
    first = identifiers(runpy.run_path(str(files / "apps" / "cluster_segment_path_app.py"), run_name="__main__"))
    sys.path.insert(0, str(files / "other"))
    second = identifiers(vars(importlib.import_module("random_image_app")))

    assert first["mode"] == second["mode"] == "@sharedlib.schema/projectionmode"
    assert first["image"] == second["image"] == "@numpy/ndarray"
    assert first["method"] == "@cluster-segment-path/thresholdmethod"
    assert second["method"] == "@random-image-generator/thresholdmethod"


def test_numpy_ndarray_keeps_its_module_identifier() -> None:
    app = App("in-memory-pipeline")
    app.memory_structure(np.ndarray)

    @app.action
    def count_objects(image: np.ndarray) -> int:
        """Count"""
        return int(image.size)

    assert count_objects(np.zeros(3)) == 3

    port = app.registry.implementations["count_objects"].definition.args[0]
    assert port.identifier == "@numpy/ndarray"
