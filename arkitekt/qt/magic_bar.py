from qtpy import QtWidgets, QtGui, QtCore
from arkitekt.app import ArkitektApp
from koil.qt import QtRunner
from koil.composition.qt import QtPedanticKoil
from .utils import get_image_path


class MagicBar(QtWidgets.QWidget):
    def __init__(self, app: ArkitektApp, dark_mode: bool = False) -> None:
        super().__init__()
        self.app = app
        assert isinstance(self.app.koil, QtPedanticKoil), "Koil should be Qt Koil"
        self.dark_mode = dark_mode

        self.connect_task = QtRunner(self.app.aconnect)
        self.connect_task.errored.connect(print)
        self.connect_task.returned.connect(self.on_connected)

        self.provide_task: QtRunner = QtRunner(self.app.arkitekt.arun)
        self.provide_task.errored.connect(print)
        self.provide_task.returned.connect(self.on_providing_ended)

        self.magicb = QtWidgets.QPushButton("Connect")
        self.magicb.setMinimumHeight(30)
        self.magicb.setMaximumHeight(30)

        self.connect_future = None
        self.provide_future = None

        self.layout = QtWidgets.QHBoxLayout()
        self.gearb_pix = QtGui.QPixmap(get_image_path("gear.png", dark_mode=dark_mode))
        self.gearb = QtWidgets.QPushButton()
        self.gearb.setIcon(QtGui.QIcon(self.gearb_pix))
        self.gearb.setMinimumWidth(30)
        self.gearb.setMaximumWidth(30)
        self.gearb.setMinimumHeight(30)
        self.gearb.setMaximumHeight(30)

        self.magicb.clicked.connect(self.magic_button_clicked)
        self.gearb.clicked.connect(self.gear_button_clicked)

        self.layout.addWidget(self.magicb)
        self.layout.addWidget(self.gearb)
        self.setLayout(self.layout)

        if not self.app.fakts.healthy:
            self.set_unkonfigured()
        else:
            self.set_unconnected()

    def on_connected(self):
        self.magicb.setText("Provide")

    def on_providing_ended(self):
        pass

    def gear_button_clicked(self):
        pass

    def update_movie(self):
        self.magicb.setIcon(QtGui.QIcon(self.magicb_movie.currentPixmap()))

    def set_button_movie(self, movie):
        self.magicb_movie = QtGui.QMovie(
            get_image_path(movie, dark_mode=self.dark_mode)
        )
        self.magicb_movie.frameChanged.connect(self.update_movie)
        self.magicb_movie.setScaledSize(QtCore.QSize(30, 30))
        self.magicb_movie.start()

    def set_unkonfigured(self):
        self.set_button_movie("pink pulse.gif")
        self.magicb.setDisabled(False)
        self.magicb.setText("Konfigure App")

    def set_unconnected(self):
        self.set_button_movie("green pulse.gif")
        self.magicb.setDisabled(False)
        self.magicb.setText("Connect")

    def magic_button_clicked(self):
        if not self.connect_future:
            self.connect_future = self.connect_task.run()
            self.magicb.setText("Cancel Login")
            return
        if not self.connect_future.done():
            self.connect_future.cancel()
            self.magicb.setText("Login")
            return

        if not self.provide_future:
            self.provide_future = self.provide_task.run()
            self.magicb.setText("Cancel Providing...")
            return
        if not self.provide_future.done():
            self.provide_future.cancel()
            self.magicb.setText("Provide")
            return
