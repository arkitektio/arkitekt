"""A Qt app is a declaration like any other; a MagicBar drives a run of it.

Registering happens on the QtApp (in a widget's constructor, typically) and the
bar is handed ``connect(app)`` -- a runtime that is not entered yet, so nothing
the bar does at construction may reach for fakts or the agent.
"""

from typing import Any

import pytest

# qtpy is a dev dependency, but a *binding* (PyQt/PySide) is deliberately left to
# the application -- so importing qtpy succeeds and then raises when it looks for
# one. Skipping on that is what keeps these runnable wherever a binding exists.
try:
    from qtpy import QtCore  # noqa: F401
except Exception as exc:  # pragma: no cover -- environment-dependent
    pytest.skip(f"no Qt bindings available: {exc}", allow_module_level=True)

pytestmark = pytest.mark.qt

from arkitekt import connect  # noqa: E402
from arkitekt.qt.types import QtApp  # noqa: E402


@pytest.fixture(scope="module")
def qapp() -> Any:
    from qtpy import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def build_qt_app(identifier: str = "qt-app", **kwargs: Any) -> QtApp:
    from qtpy import QtCore

    return QtApp(identifier, parent=QtCore.QObject(), **kwargs)


def test_a_qt_app_is_a_declaration(qapp: Any) -> None:
    app = build_qt_app("declared", version="1.2")

    assert (app.identifier, app.version) == ("declared", "1.2")
    assert app.parent is not None


@pytest.mark.parametrize(
    "method",
    [
        "action",
        "register_in_qt_loop",
        "register_with_qt_future",
        "register_with_qt_generator",
    ],
)
def test_registering_on_a_qt_app(qapp: Any, method: str) -> None:
    """Each Qt actifier reaches the app's own registry, and makes the app use rekuest."""
    from koil.qt import QtFuture, QtGenerator

    app = build_qt_app(f"reg-{method}")

    # Each actifier demands its own first parameter, which is exactly the check
    # that proves the call reached the real actifier rather than being swallowed.
    if method == "register_with_qt_future":

        def implementation(future: QtFuture[int], x: int) -> None:
            future.resolve(x)

    elif method == "register_with_qt_generator":

        def implementation(gen: QtGenerator[int], x: int) -> None:
            gen.next(x)

    else:

        def implementation(x: int) -> int:
            return x

    getattr(app, method)(implementation)

    assert app.registry.implementations, f"{method} registered nothing"
    assert "rekuest" not in app.services, "run() brings rekuest; the app declares only what it offers"


def test_the_magic_bar_builds_on_an_unentered_runtime(qapp: Any) -> None:
    """The bar is built before its runtime is entered: labels from the app, tasks lazy."""
    from arkitekt.qt.magic_bar import MagicBar

    app = build_qt_app("bar", version="1.2", logo=None)
    runtime = connect(app, provide=True, token="token", url="http://127.0.0.1:1", no_cache=True)
    bar = MagicBar(runtime)

    assert bar.profile.app is app
    assert bar.runtime is runtime and runtime.fakts is None
    assert bar.configure_task is not None
    assert bar.provide_task is not None
