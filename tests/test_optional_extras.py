"""The optional extras actually install what their module imports.

`arkitekt.tqdm` shipped for a long time importing a `tqdm` that was in no
dependency list, so `from arkitekt.tqdm import tqdm` raised `ModuleNotFoundError`
in every clean install. Nothing caught it because nothing imported the module --
that is exactly the shape of failure a public convenience module has.
"""

import tomllib
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _extras() -> dict[str, list[str]]:
    return tomllib.loads(PYPROJECT.read_text())["project"]["optional-dependencies"]


def test_the_tqdm_extra_declares_what_the_module_imports() -> None:
    assert any(d.startswith("tqdm") for d in _extras()["tqdm"])


def test_arkitekt_tqdm_imports() -> None:
    """Skips when the extra is not installed; fails if it is and still breaks."""
    pytest.importorskip("tqdm", reason="the `tqdm` extra is not installed")

    from arkitekt.tqdm import tqdm

    assert issubclass(tqdm, __import__("tqdm").tqdm)


def test_the_all_extra_bundles_every_service_client() -> None:
    """It claimed to, while omitting three."""
    extras = _extras()
    services = {
        name
        for name in extras
        if name not in {"all", "cli", "qt", "serve", "tqdm"}
    }
    (bundle,) = extras["all"]
    named = set(bundle.partition("[")[2].rstrip("]").split(","))
    assert named == services, f"`all` omits {sorted(services - named)}"
