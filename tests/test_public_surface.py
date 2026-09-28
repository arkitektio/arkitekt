"""``from arkitekt import ...`` is the canonical import: an app needs nothing else.

arkitekt-spec is the definition space SDKs and runtimes build on. Every spec (or
runtime) type an app meets in arkitekt's own signatures -- a parameter of
``@app.action``, the return of ``bsx``, the hook type ``Task.install_hook`` takes --
must therefore be importable from ``arkitekt`` (or ``arkitekt.widgets``), or an app
has to reach into the definition space to annotate its own code.
"""

import inspect
import re
import typing

import arkitekt
import arkitekt.widgets
from arkitekt import App, Runtime

DEFINITION_SPACE = ("arkitekt_spec", "arkitekt_runtime")


def _public_callables() -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    for owner in (App, Runtime):
        for name, member in inspect.getmembers(owner):
            if not name.startswith("_") and callable(member):
                found.append((f"{owner.__name__}.{name}", member))
    for name in arkitekt.__all__:
        member = getattr(arkitekt, name)
        if inspect.isfunction(member):
            found.append((name, member))
    task = arkitekt.Task
    for name, member in inspect.getmembers(task):
        if not name.startswith("_") and callable(member):
            found.append((f"Task.{name}", member))
    return found


def _named_types(annotation: object) -> set[tuple[str, str]]:
    """``(module, name)`` of every class an annotation spells out."""
    return {
        (module, name)
        for module, name in (
            dotted.rsplit(".", 1)
            for dotted in re.findall(r"\b(?:arkitekt_spec|arkitekt_runtime)[\w.]*\.\w+", repr(annotation))
        )
    }


def test_every_definition_type_in_a_public_signature_is_exported() -> None:
    exported = set(arkitekt.__all__) | set(arkitekt.widgets.__all__)
    missing: dict[str, set[str]] = {}
    for where, member in _public_callables():
        try:
            hints = typing.get_type_hints(member)
        except Exception:  # noqa: BLE001 -- an unresolvable hint is not this test's concern
            continue
        for parameter, annotation in hints.items():
            for module, name in _named_types(annotation):
                if module.startswith(DEFINITION_SPACE) and name not in exported:
                    missing.setdefault(f"{module}.{name}", set()).add(f"{where}({parameter})")
    assert not missing, missing


def test_the_task_an_app_annotates_can_report_and_call() -> None:
    for member in (
        "id", "user", "org", "token",
        "log", "alog", "progress", "aprogress", "pausepoint", "apausepoint", "install_hook",
        "call", "acall", "iterate", "aiterate", "local",
    ):
        assert hasattr(arkitekt.Task, member), member


def test_every_exported_name_resolves() -> None:
    assert [n for n in arkitekt.__all__ if not hasattr(arkitekt, n)] == []
    assert [n for n in arkitekt.widgets.__all__ if not hasattr(arkitekt.widgets, n)] == []
