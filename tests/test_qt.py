from arkitekt.builders import publicqt
from arkitekt.qt.magic_bar import MagicBar
import pytest
from qtpy import QtWidgets, QtCore
from koil.qt import QtRunner
import time


class QtArkitektWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = publicqt("countries", "latest", no_cache=True, parent=self)

        self.magic_bar = MagicBar(self.app)
        self.runner = QtRunner(self.app.fakts.aget)

        self.button_greet = QtWidgets.QPushButton("Greet")
        self.greet_label = QtWidgets.QLabel("")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.button_greet)
        layout.addWidget(self.greet_label)

        self.setLayout(layout)

        self.button_greet.clicked.connect(self.greet)

    def greet(self):
        self.app.fakts.get("fakts")


@pytest.mark.qt
def test_qteasy(qtbot):
    widget = QtArkitektWidget()
    qtbot.addWidget(widget)

    with qtbot.waitSignal(
        widget.magic_bar.configure_task.errored, timeout=9000, raising=True
    ) as p:
        qtbot.mouseClick(
            widget.magic_bar.magicb,
            QtCore.Qt.LeftButton,
        )

        def visible():
            assert (
                widget.app.fakts.grant.grant.discovery.widget.isVisible()
            ), "Widget is not visible"

        qtbot.waitUntil(visible)
        cancel_button = widget.app.fakts.grant.grant.discovery.widget.on_reject()
