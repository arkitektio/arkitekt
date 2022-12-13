from enum import Enum
from qtpy import QtWidgets, QtGui, QtCore
from koil.qt import QtRunner
from arkitekt.apps.rekuest import RekuestApp
from .utils import get_image_path


class Profile(QtWidgets.QDialog):
    def __init__(
        self,
        app: RekuestApp,
        bar: "MagicBar",
        *args,
        dark_mode: bool = False,
        **kwargs,
    ):
        super(Profile, self).__init__(*args, parent=bar, **kwargs)
        self.app = app
        self.bar = bar

        self.setWindowTitle("Profile")
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.logout_button = QtWidgets.QPushButton("Logout")
        self.logout_button.clicked.connect(lambda: self.bar.logout_task.run())

        self.unkonfigure_button = QtWidgets.QPushButton("Unkonfirug")
        self.unkonfigure_button.clicked.connect(
            lambda: self.bar.configure_task.run(force_refresh=True)
        )

        self.layout.addWidget(self.logout_button)
        self.layout.addWidget(self.unkonfigure_button)


class AppState(str, Enum):
    READY = "ready"
    DOWN = "down"
    UP = "up"


class ProcessState(str, Enum):
    UNKONFIGURED = "unkonfigured"
    UNLOGGED = "unlogged"
    UNPROVIDED = "unprovided"
    PROVIDING = "providing"


class MagicBar(QtWidgets.QWidget):
    app_up = QtCore.Signal()
    app_down = QtCore.Signal()
    app_error = QtCore.Signal()
    state = AppState.DOWN
    process_state = ProcessState.UNKONFIGURED

    def __init__(self, app: RekuestApp, dark_mode: bool = False) -> None:
        super().__init__()
        self.app = app
        # assert isinstance(
        #     self.app.koil, QtPedanticKoil
        # ), f"Koil should be Qt Koil but is {type(self.app.koil)}"
        self.dark_mode = dark_mode

        self.profile = Profile(app, self, dark_mode=dark_mode)

        self.configure_task = QtRunner(self.app.fakts.aload)
        self.configure_task.errored.connect(self.configure_errored)
        self.configure_task.returned.connect(self.set_unlogined)

        self.login_task = QtRunner(self.app.herre.alogin)
        self.login_task.errored.connect(self.login_errored)
        self.login_task.returned.connect(self.set_unprovided)

        self.logout_task = QtRunner(self.app.herre.alogout)
        self.logout_task.errored.connect(self.task_errored)
        self.logout_task.returned.connect(self.set_unlogined)

        self.provide_task: QtRunner = QtRunner(self.app.rekuest.agent.aprovide)
        self.provide_task.errored.connect(self.provide_errored)
        self.provide_task.returned.connect(self.set_unprovided)

        self.magicb = QtWidgets.QPushButton("Connect")
        self.magicb.setMinimumHeight(30)
        self.magicb.setMaximumHeight(30)

        self.configure_future = None
        self.login_future = None
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

        self.set_unkonfigured()

    def task_errored(self, ex: Exception):
        raise ex

    def configure_errored(self, ex: Exception):
        self.set_unkonfigured()
        raise ex

    def login_errored(self, ex: Exception):
        self.set_unlogined()
        raise ex

    def provide_errored(self, ex: Exception):
        self.set_unprovided()
        raise ex

    def on_configured(self):
        set.set

    def on_login(self):
        self.magicb.setText("Provide")

    def on_provided(self):
        self.magicb.setText("Provide ended")

    def on_providing_ended(self):
        pass

    def gear_button_clicked(self):
        self.profile.show()

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
        self.state = AppState.DOWN
        self.process_state = ProcessState.UNKONFIGURED
        self.app_down.emit()
        self.set_button_movie("pink pulse.gif")
        self.profile.unkonfigure_button.setDisabled(True)
        self.profile.logout_button.setDisabled(True)
        self.magicb.setDisabled(False)
        self.magicb.setText("Konfigure App")

    def set_unlogined(self):
        self.state = AppState.DOWN
        self.process_state = ProcessState.UNLOGGED
        self.app_down.emit()
        self.set_button_movie("orange pulse.gif")
        self.profile.unkonfigure_button.setDisabled(False)
        self.profile.logout_button.setDisabled(True)
        self.magicb.setDisabled(False)
        self.magicb.setText("Login")

    def set_unprovided(self):
        self.state = AppState.UP
        self.process_state = ProcessState.UNPROVIDED
        self.app_up.emit()
        self.set_button_movie("green pulse.gif")
        self.profile.unkonfigure_button.setDisabled(False)
        self.profile.logout_button.setDisabled(False)
        self.magicb.setDisabled(False)
        self.magicb.setText("Provide")

    def set_providing(self):
        self.state = AppState.UP
        self.process_state = ProcessState.PROVIDING
        self.app_up.emit()
        self.set_button_movie("red pulse.gif")
        self.profile.unkonfigure_button.setDisabled(False)
        self.profile.logout_button.setDisabled(False)
        self.magicb.setDisabled(False)
        self.magicb.setText("Cancel Provide..")

    def magic_button_clicked(self):
        if self.process_state == ProcessState.UNKONFIGURED:
            if not self.configure_future or self.configure_future.done():
                self.configure_future = self.configure_task.run()
                self.magicb.setText("Cancel Configuration")
                return
            if not self.configure_future.done():
                self.configure_future.cancel()
                self.set_unkonfigured()
                return

        if self.process_state == ProcessState.UNLOGGED:
            if not self.login_future or self.login_future.done():
                self.login_future = self.login_task.run()
                self.magicb.setText("Cancel Login")
                return
            if not self.login_future.done():
                self.login_future.cancel()
                self.magicb.setText("Login")
                self.set_unlogined()
                return

        if self.process_state == ProcessState.UNPROVIDED:
            if not self.provide_future or self.provide_future.done():
                self.provide_future = self.provide_task.run()
                self.set_providing()
                return

        if self.process_state == ProcessState.PROVIDING:
            if not self.provide_future.done():
                self.provide_future.cancel()
                self.set_unprovided()
                return
