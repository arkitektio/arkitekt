"""The optional extras actually install what their module imports.

`arkitekt.tqdm` shipped for a long time importing a `tqdm` that was in no
dependency list, so `from arkitekt.tqdm import tqdm` raised `ModuleNotFoundError`
in every clean install. Nothing caught it because nothing imported the module --
that is exactly the shape of failure a public convenience module has.
"""

import io
import tomllib
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _extras() -> dict[str, list[str]]:
    return tomllib.loads(PYPROJECT.read_text())["project"]["optional-dependencies"]


def test_the_tqdm_extra_declares_what_the_module_imports() -> None:
    assert any(d.startswith("tqdm") for d in _extras()["tqdm"])


def test_arkitekt_tqdm_imports() -> None:
    """Skips when the extra is not installed; fails if it is and still breaks.

    It broke twice over: `tqdm` was in no dependency list, and the class wrote
    `_tqdm[T]`, which only resolves under a type checker -- `tqdm` is generic in
    `types-tqdm` and a plain class at runtime, so the module raised `TypeError`
    on import even once the dependency arrived.
    """
    pytest.importorskip("tqdm", reason="the `tqdm` extra is not installed")

    from arkitekt.tqdm import tqdm

    assert issubclass(tqdm, __import__("tqdm").tqdm)


def test_arkitekt_tqdm_reports_to_the_task_it_is_handed() -> None:
    """The one thing the subclass exists for, never exercised until now."""
    pytest.importorskip("tqdm", reason="the `tqdm` extra is not installed")

    from arkitekt_spec.declare.task import LocalTask

    from arkitekt.tqdm import tqdm

    reported: list[int] = []

    class RecordingTask(LocalTask):
        def progress(self, percentage: int, message: str | None = None) -> None:
            reported.append(percentage)

    # Not `disable=True`: tqdm's disabled `__iter__` is a fast path that never
    # calls `update`, so the reporting this exists for would never run.
    consumed = list(
        tqdm(
            range(100),
            task=RecordingTask(),
            file=io.StringIO(),
            mininterval=0,
        )
    )

    assert consumed == list(range(100))
    assert reported and reported == sorted(reported)
    assert reported[-1] >= 90, reported


def test_arkitekt_tqdm_without_a_task_is_a_plain_tqdm() -> None:
    pytest.importorskip("tqdm", reason="the `tqdm` extra is not installed")

    from arkitekt.tqdm import tqdm

    assert list(tqdm(range(5), file=io.StringIO())) == list(range(5))


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
