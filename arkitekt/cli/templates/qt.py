""" An example of a Qt app for Arkitekt: a window of its own, that others can call"""

import sys
from typing import Optional

from qtpy import QtWidgets

from arkitekt import connect
from arkitekt.qt import MagicBar, QtApp

# The version of the app.
__version__ = __APP_VERSION__


class Window(QtWidgets.QWidget):
    """The app's window: what it shows, and the bar that connects it.

    It is also the app's context: an action that asks for a `Window` is handed
    this one.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(app.identifier)

        self.message = QtWidgets.QLabel("Nothing was shown yet")

        # One run of the app, with this window as its context. The bar logs it in
        # and starts it, at the press of a button.
        self.runtime = connect(app, provide=True)
        self.bar = MagicBar(self.runtime, context=self)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.message)
        layout.addWidget(self.bar)
        self.setLayout(layout)


# The app is a declaration: who it is, what it offers, and the class of its
# context. The window above runs it; `arkitekt check` and the tests find it in
# this module (as `app`).
app = QtApp(__APP_ARGUMENTS__, app_context=Window)


# An action like any other: it runs in a thread of its own, beside the window.


@app.action
def count_words(text: str) -> int:
    """Count Words

    Counts the words of a text

    Parameters
    ----------
    text : str
        The text to count the words of

    Returns
    -------
    int
        How many words it has
    """
    return len(text.split())


# An action that touches the window asks for it by its class, and runs in the Qt
# loop, where widgets live. The window is not an argument of the action: a caller
# gives the text, and the app the window.


@app.register_in_qt_loop
def show_message(text: str, window: Window) -> str:
    """Show Message

    Shows a text in the window

    Parameters
    ----------
    text : str
        The text to show

    Returns
    -------
    str
        The text that was shown before
    """
    before = window.message.text()
    window.message.setText(text)
    return before


def main() -> int:
    """Open the window, and keep the app's run for as long as it is open."""
    application = QtWidgets.QApplication(sys.argv)
    window = Window()
    with window.runtime:
        window.show()
        return application.exec()


if __name__ == "__main__":
    sys.exit(main())
