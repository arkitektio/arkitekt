"""The app and its window, with no server and no screen.

`call` starts the app as a run starts it and calls an action by name. The window
is built for real, on Qt's offscreen platform, so these run anywhere a Qt
binding is installed (`uv add pyqt6`, or `pyside6`); without one they are
skipped. Run them with `uv run pytest`.
"""

import os

import pytest

# No screen is needed to build a window, unless one is asked for.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from qtpy import QtWidgets
except Exception as error:  # qtpy is installed, a binding (PyQt, PySide) may not be
    pytest.skip(f"No Qt binding is installed: `uv add pyqt6` (or pyside6). {error}", allow_module_level=True)

from arkitekt.runtime import Runtime  # noqa: E402
from arkitekt.testing import local_app  # noqa: E402

from __ENTRYPOINT__ import Window, app, show_message  # noqa: E402


@pytest.fixture(scope="module")
def window():
    """The app's window, built once for the tests of this file."""
    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = Window()
    yield window
    window.close()
    application.processEvents()


@pytest.fixture()
def arkitekt_context(window: Window) -> Window:
    """The app's context is its window: what `call` and `local_runtime` start the app with."""
    return window


def test_count_words(call):
    assert call("count_words", text="one two  three") == 3
    assert call("count_words", text="") == 0


def test_the_app_is_started_with_its_window(local_runtime: Runtime[Window], window: Window):
    assert local_runtime.app is app
    assert app.registry.app_context_class is Window


def test_the_app_does_not_start_without_a_window():
    with pytest.raises(Exception, match="Window"):
        with local_app(app):
            pass


def test_the_window_is_not_an_argument_of_the_action():
    # A caller gives the text; the window is the app's to hand in.
    definition = app.registry.implementations["show_message"].definition
    assert [port.key for port in definition.args] == ["text"]


def test_show_message_shows_it_and_returns_what_was_there(window: Window):
    # Called as the function it is: through the app it runs in the Qt loop, which
    # a test that waits for the answer would be standing in.
    assert show_message("Hello", window) == "Nothing was shown yet"
    assert window.message.text() == "Hello"
    assert show_message("again", window) == "Hello"


def test_the_bar_provides_the_app_with_its_window(window: Window):
    assert window.bar.runtime is window.runtime
    assert window.bar.context is window
    assert window.runtime.app is app
