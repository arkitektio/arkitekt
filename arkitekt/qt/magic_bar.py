from enum import Enum
from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget
from qtpy import QtWidgets, QtGui, QtCore
import urllib
from arkitekt.apps.qt import QtApp
from koil.qt import async_to_qt
from arkitekt import App
from .utils import get_image_path
from typing import Optional, Callable
import logging
import aiohttp

logger = logging.getLogger(__name__)


class Logo(QtWidgets.QWidget):
    def __init__(self, url: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.logo_url = url
        self.getter = async_to_qt(
            self.aget_image,
        )

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        self.getter.returned.connect(self.on_image)
        self.getter.run()

    def on_image(self, data: bytes):
        self.pixmap = QtGui.QPixmap()
        self.pixmap.loadFromData(data)
        self.scaled_pixmap = self.pixmap.scaledToWidth(100)
        self.logo = QtWidgets.QLabel()
        self.logo.setPixmap(self.scaled_pixmap)

        self.layout.addWidget(self.logo)

    async def aget_image(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.logo_url) as resp:
                if resp.status == 200 and "image" in resp.headers["Content-Type"]:
                    data = await resp.read()
                    return data
                else:
                    print(f"Failed to download the image. Status code: {resp.status}")
                    return None


class ArkitektLogsRetriever(logging.Handler, QtCore.QObject):
    appendPlainText = QtCore.Signal(str)

    def __init__(self, widget: QtWidgets.QPlainTextEdit, *args, **kwargs):
        super().__init__()
        QtCore.QObject.__init__(self)
        self.appendPlainText.connect(widget.appendPlainText)
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s"
            )
        )

    def emit(self, record):
        msg = self.format(record)
        self.appendPlainText.emit(msg)


class ArkitektLogs(QtWidgets.QDialog):
    def __init__(self, settings: QtCore.QSettings, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.settings = settings
        self.setWindowTitle("Logs")
        self.layout = QtWidgets.QVBoxLayout()
        self.text = QtWidgets.QPlainTextEdit(parent=self)
        self.text.setMaximumBlockCount(5000)
        self.text.setReadOnly(True)
        self.layout.addWidget(self.text)
        self.logRetriever = ArkitektLogsRetriever(self.text)
        logging.getLogger().addHandler(self.logRetriever)
        logging.getLogger().setLevel(self.log_level)
        self.setLayout(self.layout)

    def update_log_level(self, level: str):
        logging.getLogger().setLevel(level)
        self.settings.setValue("log_level", level)

    @property
    def log_to_file(self):
        return self.settings.value("log_to_file", False, bool)

    @property
    def log_level(self):
        return self.settings.value("log_level", "INFO", str)


class Profile(QtWidgets.QDialog):
    updated = QtCore.Signal()

    def __init__(
        self,
        app: QtApp,
        bar: "MagicBar",
        *args,
        dark_mode: bool = False,
        **kwargs,
    ) -> None:
        super(Profile, self).__init__(*args, parent=bar, **kwargs)
        self.app = app
        self.bar = bar

        self.settings = QtCore.QSettings(
            "arkitekt",
            f"{self.app.manifest.identifier}:{self.app.manifest.version}:profile",
        )

        self.setWindowTitle("Settings")

        self.infobar = QtWidgets.QVBoxLayout()

        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.layout.addLayout(self.infobar)

        if self.app.manifest.logo:
            self.infobar.addWidget(Logo(self.app.manifest.logo, parent=self))

        self.infobar.addWidget(QtWidgets.QLabel(self.app.manifest.identifier))
        self.infobar.addWidget(QtWidgets.QLabel(self.app.manifest.version))

        self.logout_button = QtWidgets.QPushButton("Change User")
        self.logout_button.clicked.connect(
            lambda: self.bar.refresh_token_task.run(
                allow_cache=False, allow_refresh=False, allow_auto_login=False
            )
        )

        self.unkonfigure_button = QtWidgets.QPushButton("Change Server")
        self.unkonfigure_button.clicked.connect(
            lambda: self.bar.refresh_task.run(
                allow_auto_demand=False,
                allow_auto_discover=False,
            )
        )

        button_bar = QtWidgets.QHBoxLayout()
        self.infobar.addLayout(button_bar)
        button_bar.addWidget(self.logout_button)
        button_bar.addWidget(self.unkonfigure_button)

        self.logs = ArkitektLogs(self.settings, parent=self)

        self.go_all_the_way_button = QtWidgets.QPushButton("One click provide")
        self.go_all_the_way_button.setCheckable(True)
        self.go_all_the_way_button.setChecked(self.go_all_the_way_down)
        self.go_all_the_way_button.clicked.connect(self.on_go_all_the_way_clicked)

        self.sidebar = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.sidebar)

        self.show_logs_button = QtWidgets.QPushButton("Show Logs")
        self.show_logs_button.clicked.connect(self.logs.show)

        self.sidebar.addWidget(self.go_all_the_way_button)
        self.sidebar.addWidget(self.show_logs_button)
        self.sidebar.addStretch()

    def on_go_all_the_way_clicked(self, checked: bool) -> None:
        self.settings.setValue("go_all_the_way_down", checked)
        self.updated.emit()

    @property
    def go_all_the_way_down(self) -> bool:
        return self.settings.value("go_all_the_way_down", True, bool)


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
    """The magic bar is a small button widget, that can be used to configure, login and put the
    app up and down. (providing and non providing). It also has a gear button that opens the
    settings dialog. To adjust some parameters of the app"""

    CONNECT_LABEL = "Connect"

    app_state_changed = QtCore.Signal()
    app_up = QtCore.Signal()
    app_down = QtCore.Signal()
    app_error = QtCore.Signal()
    state = AppState.DOWN
    process_state = ProcessState.UNKONFIGURED

    def __init__(
        self,
        app: App,
        dark_mode: bool = False,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        super().__init__()
        self.app = app

        # assert isinstance(
        #     self.app.koil, QtPedanticKoil
        # ), f"Koil should be Qt Koil but is {type(self.app.koil)}"
        self.dark_mode = dark_mode

        self.profile = Profile(app, self, dark_mode=dark_mode)
        self.profile.updated.connect(self.on_profile_updated)

        self.configure_task = async_to_qt(self.app.fakts.aget)
        self.configure_task.errored.connect(self.configure_errored)
        self.configure_task.returned.connect(self.set_unlogined)

        self.refresh_task = async_to_qt(self.app.fakts.arefresh)
        self.refresh_task.errored.connect(self.configure_errored)
        self.refresh_task.returned.connect(self.set_unlogined)

        self.get_token_task = async_to_qt(self.app.herre.aget_token)
        self.get_token_task.errored.connect(self.login_errored)
        self.get_token_task.returned.connect(self.set_unprovided)

        self.refresh_token_task = async_to_qt(self.app.herre.arefresh_token)
        self.refresh_token_task.started.connect(self.set_providing)
        self.refresh_token_task.errored.connect(self.login_errored)
        self.refresh_token_task.returned.connect(self.set_unprovided)

        self.provide_task = async_to_qt(self.app.rekuest.agent.aprovide)
        self.provide_task.errored.connect(self.provide_errored)
        self.provide_task.returned.connect(self.set_unprovided)

        self.magicb = QtWidgets.QPushButton(MagicBar.CONNECT_LABEL)
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
        self._on_error = on_error

        self.magicb.clicked.connect(self.magic_button_clicked)
        self.gearb.clicked.connect(self.gear_button_clicked)

        self.layout.addWidget(self.magicb)
        self.layout.addWidget(self.gearb)
        self.setLayout(self.layout)

        self.set_unkonfigured()
        self.on_profile_updated()

    def on_profile_updated(self):
        if self.profile.go_all_the_way_down:
            self.set_unprovided()

    def show_error(self, ex: Exception):
        if self._on_error:
            self._on_error(ex)
        else:
            logger.error(f"Error {repr(ex)}")

    def task_errored(self, ex: Exception):
        raise ex

    def configure_errored(self, ex: Exception):
        self.set_unkonfigured()
        self.show_error(ex)

    def login_errored(self, ex: Exception):
        self.set_unlogined()
        self.show_error(ex)

    def provide_errored(self, ex: Exception):
        self.set_unprovided()
        self.show_error(ex)

    def on_configured(self):
        self.magicb.setText("Login")

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
        self.app_state_changed.emit()
        self.set_button_movie("pink pulse.gif")
        self.profile.unkonfigure_button.setDisabled(True)
        self.profile.logout_button.setDisabled(True)
        self.magicb.setDisabled(False)
        self.magicb.setText("Konfigure App")

    def set_unlogined(self):
        self.state = AppState.DOWN
        self.process_state = ProcessState.UNLOGGED
        self.app_down.emit()

        self.app_state_changed.emit()
        self.set_button_movie("orange pulse.gif")
        self.profile.unkonfigure_button.setDisabled(False)
        self.profile.logout_button.setDisabled(True)
        self.magicb.setDisabled(False)
        self.magicb.setText("Login")

    def set_unprovided(self):
        self.state = AppState.UP
        self.process_state = ProcessState.UNPROVIDED
        self.app_up.emit()

        self.app_state_changed.emit()
        self.set_button_movie("green pulse.gif")
        self.profile.unkonfigure_button.setDisabled(False)
        self.profile.logout_button.setDisabled(False)
        self.magicb.setDisabled(False)
        self.magicb.setText("Provide")

    def set_providing(self):
        self.state = AppState.UP
        self.process_state = ProcessState.PROVIDING
        self.app_up.emit()

        self.app_state_changed.emit()
        self.set_button_movie("red pulse.gif")
        self.profile.unkonfigure_button.setDisabled(False)
        self.profile.logout_button.setDisabled(False)
        self.magicb.setDisabled(False)
        self.magicb.setText("Cancel Provide..")

    def magic_button_clicked(self):
        if (
            self.process_state == ProcessState.UNKONFIGURED
            and not self.profile.go_all_the_way_down
        ):
            if not self.configure_future or self.configure_future.done():
                self.configure_future = self.configure_task.run()
                self.magicb.setText("Cancel Configuration")
                return
            if not self.configure_future.done():
                self.configure_future.cancel()
                self.set_unkonfigured()
                return

        if (
            self.process_state == ProcessState.UNLOGGED
            and not self.profile.go_all_the_way_down
        ):
            if not self.login_future or self.login_future.done():
                self.login_future = self.get_token_task.run()
                self.magicb.setText("Cancel Login")
                return
            if not self.login_future.done():
                self.login_future.cancel()
                self.magicb.setText("Login")
                self.set_unlogined()
                return

        if (
            self.process_state != ProcessState.PROVIDING
            or self.profile.go_all_the_way_down
        ):
            if not self.provide_future or self.provide_future.done():
                self.provide_future = self.provide_task.run()
                self.set_providing()
                return

        if not self.provide_future.done():
            self.provide_future.cancel()
            self.set_unprovided()
            return
