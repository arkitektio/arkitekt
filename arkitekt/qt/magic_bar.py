from enum import Enum
from qtpy import QtWidgets, QtGui, QtCore
from arkitekt.apps.qt import QtApp
from koil.qt import async_to_qt
from .utils import get_image_path
from typing import Optional, Callable
import logging
import aiohttp
from logging import LogRecord

logger = logging.getLogger(__name__)


class Logo(QtWidgets.QWidget):
    """Logo widget

    THhe logo widget is a widget that can be used to display a logo in the settings dialog.
    It will download the logo from the url, and display it.


    """

    def __init__(self, url: str, *args, **kwargs) -> None:
        """Logo widget

        Parameters
        ----------
        url : str
            The url to download the logo from.
        """

        super().__init__(*args, **kwargs)
        self.logo_url = url
        self.getter = async_to_qt(
            self.aget_image,
        )  # we use async_to_qt to convert the async function to a Qt signal. (see koil docs)

        self.mylayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mylayout)
        self.getter.returned.connect(self.on_image)
        self.getter.run()

    def on_image(self, data: Optional[bytes]) -> None:
        """Callback for when the image is downloaded."""
        if not data:
            return

        self.pixmap = QtGui.QPixmap()
        self.pixmap.loadFromData(data)
        self.scaled_pixmap = self.pixmap.scaledToWidth(100)
        self.logo = QtWidgets.QLabel()
        self.logo.setPixmap(self.scaled_pixmap)

        self.mylayout.addWidget(self.logo)

    async def aget_image(self) -> Optional[bytes]:
        """Async function to download the image."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.logo_url) as resp:
                if resp.status == 200 and "image" in resp.headers["Content-Type"]:
                    data = await resp.read()
                    return data
                else:
                    print(f"Failed to download the image. Status code: {resp.status}")
                    return None


class ArkitektLogsRetriever(logging.Handler, QtCore.QObject):
    """A logging handler that will emit a Qt signal when a log message is received."""

    appendPlainText = QtCore.Signal(str)

    def __init__(self, widget: QtWidgets.QPlainTextEdit, *args, **kwargs) -> None:
        """A logging handler that will emit a Qt signal when a log message is received.

        Parameters
        ----------
        widget : QtWidgets.QPlainTextEdit
            A plain text edit widget to display the logs in.
        """
        super().__init__()
        QtCore.QObject.__init__(self)
        self.appendPlainText.connect(widget.appendPlainText)
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s"
            )
        )

    def emit(self, record: LogRecord) -> None:
        """Emit a Qt signal when a log message is received."""
        msg = self.format(record)
        self.appendPlainText.emit(msg)


class ArkitektLogs(QtWidgets.QDialog):
    """A dialog that will display the logs of the app."""

    def __init__(
        self,
        settings: QtCore.QSettings,
        *args,
        log_level_key: str = "log_level",
        log_to_file_key: str = "log_to_file",
        **kwargs,
    ) -> None:
        """A dialog that will display the logs of the app.

        Parameters
        ----------
        settings : QtCore.QSettings
            The settings object to use to store the log level. (so that is persistent,
            and can be changed by the user)
        log_level_key : str, optional
            The key to use to store the log level, by default "log_level"
        log_to_file_key : str, optional
            The key to use to store whether the logs should be written to a file,
             by default "log_to_file"
        """
        super().__init__(*args, **kwargs)
        self.log_level_key = log_level_key
        self.log_to_file_key = log_to_file_key
        self.settings = settings
        self.setWindowTitle("Logs")
        self.mylayout = QtWidgets.QVBoxLayout()
        self.text = QtWidgets.QPlainTextEdit(parent=self)
        self.text.setMaximumBlockCount(5000)
        self.text.setReadOnly(True)
        self.mylayout.addWidget(self.text)
        self.logRetriever = ArkitektLogsRetriever(self.text)
        logging.getLogger().addHandler(self.logRetriever)
        logging.getLogger().setLevel(self.log_level)
        self.setLayout(self.mylayout)

    def update_log_level(self, level: str) -> None:
        """Update the log level.

        Parameters
        ----------
        level : str
           Update the log level to this level.
        """
        logging.getLogger().setLevel(level)
        self.settings.setValue(self.log_level_key, level)

    @property
    def log_to_file(self) -> bool:
        """Should the logs be written to a file."""
        return self.settings.value(self.log_to_file_key, False, bool)

    @property
    def log_level(self) -> str:
        """The log level in use."""
        return self.settings.value(self.log_level_key, "INFO", str)


class Profile(QtWidgets.QDialog):
    """The profile dialog.

    It will display the logo, and allow the user to change the user, and server.
    It will also allow the user to change the log level, and show the logs on
    demand.


    """

    updated = QtCore.Signal()

    def __init__(
        self,
        app: QtApp,
        bar: "MagicBar",
        *args,
        dark_mode: bool = False,
        **kwargs,
    ) -> None:
        """The profile dialog.

        Parameters
        ----------
        app : QtApp
            The app to use. (needs to be a QtApp as it uses Qt signals)
        bar : MagicBar
            The magic bar to use and to update when the user changes the settings.
        dark_mode : bool, optional
            Should we use dark_mode, by default False
            TODO: implement dark mode
        """
        super().__init__(*args, **{"parent": bar, **kwargs})
        self.app = app
        self.bar = bar

        self.settings = QtCore.QSettings(
            "arkitekt",
            f"{self.app.manifest.identifier}:{self.app.manifest.version}:profile",
        )

        self.setWindowTitle("Settings")

        self.infobar = QtWidgets.QVBoxLayout()

        self.mylayout = QtWidgets.QHBoxLayout()
        self.setLayout(self.mylayout)
        self.mylayout.addLayout(self.infobar)

        if self.app.manifest.logo:
            self.infobar.addWidget(Logo(self.app.manifest.logo, parent=self))

        self.infobar.addWidget(QtWidgets.QLabel(self.app.manifest.identifier))
        self.infobar.addWidget(QtWidgets.QLabel(self.app.manifest.version))

        self.logout_button = QtWidgets.QPushButton("Change User")
        self.logout_button.clicked.connect(
            lambda: self.bar.refresh_token_task.run(
                allow_cache=False,
                allow_refresh=False,
                allow_auto_login=False,
                delete_active=True,
            )
        )

        self.unkonfigure_button = QtWidgets.QPushButton("Change Server")
        self.unkonfigure_button.clicked.connect(
            lambda: self.bar.refresh_task.run(
                allow_auto_demand=False,
                allow_auto_discover=False,
                delete_active=True,
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
        self.mylayout.addLayout(self.sidebar)

        self.show_logs_button = QtWidgets.QPushButton("Show Logs")
        self.show_logs_button.clicked.connect(self.logs.show)

        self.sidebar.addWidget(self.go_all_the_way_button)
        self.sidebar.addWidget(self.show_logs_button)
        self.sidebar.addStretch()

    def on_go_all_the_way_clicked(self, checked: bool) -> None:
        """Callback for when the go all the way button is clicked.

        Will update the settings, and emit the updated signal.

        Parameters
        ----------
        checked : bool
            Whether the button is checked or not.

        """
        self.settings.setValue("go_all_the_way_down", checked)
        self.updated.emit()

    @property
    def go_all_the_way_down(self) -> bool:
        """Should the app go all the way down when the user clicks the magic button."""
        return self.settings.value("go_all_the_way_down", True, bool)


class AppState(str, Enum):
    """The state of the app."""

    READY = "ready"
    DOWN = "down"
    UP = "up"


class ProcessState(str, Enum):
    UNKONFIGURED = "unkonfigured"
    UNLOGGED = "unlogged"
    UNPROVIDED = "unprovided"
    PROVIDING = "providing"


class MagicBar(QtWidgets.QWidget):
    """Magic bar widget.

    The magic bar is a small button widget, that can be used to configure, login and put the
    app in providing and non providing states.. It also has a gear button that opens the
    profile dialog. To adjust some parameters of the app"""

    CONNECT_LABEL = "Connect"

    app_state_changed = QtCore.Signal()
    app_up = QtCore.Signal()
    app_down = QtCore.Signal()
    app_error = QtCore.Signal()
    state = AppState.DOWN
    process_state = ProcessState.UNKONFIGURED

    def __init__(
        self,
        app: QtApp,
        dark_mode: bool = False,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        """Magic bar Widget

        This widget is a small button widget, that can be used to configure, login and put the
        app in providing and non providing states.. It also has a gear button that opens the
        profile dialog, that can be used to adjust some parameters of the qt app.

        Parameters
        ----------
        app : QtApp
            A qt app to use.
        dark_mode : bool, optional
            Should we use the dark mode, by default False
        on_error : Optional[Callable[[Exception], None]], optional
            And additinal callback if an error is raised, by default None
        """
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

        self.mylayout = QtWidgets.QHBoxLayout()
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

        self.mylayout.addWidget(self.magicb)
        self.mylayout.addWidget(self.gearb)
        self.setLayout(self.mylayout)

        self.set_unkonfigured()
        self.on_profile_updated()

    def on_profile_updated(self) -> None:
        """Callback for when the profile is updated."""
        if self.profile.go_all_the_way_down:
            self.set_unprovided()

    def show_error(self, ex: Exception) -> None:
        """Show an error message

        Parameters
        ----------
        ex : Exception
            The exception to show.
        """
        if self._on_error:
            self._on_error(ex)
        else:
            logger.error(f"Error {repr(ex)}")

    def task_errored(self, ex: Exception) -> None:
        """_summary_

        Parameters
        ----------
        ex : Exception
            _description_

        Raises
        ------
        ex
            _description_
        """
        raise ex

    def configure_errored(self, ex: Exception) -> None:
        self.set_unkonfigured()
        self.show_error(ex)

    def login_errored(self, ex: Exception) -> None:
        self.set_unlogined()
        self.show_error(ex)

    def provide_errored(self, ex: Exception) -> None:
        self.set_unprovided()
        self.show_error(ex)

    def on_configured(self) -> None:
        self.magicb.setText("Login")

    def on_login(self) -> None:
        self.magicb.setText("Provide")

    def on_provided(self) -> None:
        self.magicb.setText("Provide ended")

    def on_providing_ended(self) -> None:
        pass

    def gear_button_clicked(self) -> None:
        self.profile.show()

    def update_movie(self) -> None:
        self.magicb.setIcon(QtGui.QIcon(self.magicb_movie.currentPixmap()))

    def set_button_movie(self, movie) -> None:
        self.magicb_movie = QtGui.QMovie(
            get_image_path(movie, dark_mode=self.dark_mode)
        )
        self.magicb_movie.frameChanged.connect(self.update_movie)
        self.magicb_movie.setScaledSize(QtCore.QSize(30, 30))
        self.magicb_movie.start()

    def set_unkonfigured(self) -> None:
        self.state = AppState.DOWN
        self.process_state = ProcessState.UNKONFIGURED
        self.app_down.emit()
        self.app_state_changed.emit()
        self.set_button_movie("pink pulse.gif")
        self.profile.unkonfigure_button.setDisabled(True)
        self.profile.logout_button.setDisabled(True)
        self.magicb.setDisabled(False)
        self.magicb.setText("Konfigure App")

    def set_unlogined(self) -> None:
        self.state = AppState.DOWN
        self.process_state = ProcessState.UNLOGGED
        self.app_down.emit()

        self.app_state_changed.emit()
        self.set_button_movie("orange pulse.gif")
        self.profile.unkonfigure_button.setDisabled(False)
        self.profile.logout_button.setDisabled(True)
        self.magicb.setDisabled(False)
        self.magicb.setText("Login")

    def set_unprovided(self) -> None:
        self.state = AppState.UP
        self.process_state = ProcessState.UNPROVIDED
        self.app_up.emit()

        self.app_state_changed.emit()
        self.set_button_movie("green pulse.gif")
        self.profile.unkonfigure_button.setDisabled(False)
        self.profile.logout_button.setDisabled(False)
        self.magicb.setDisabled(False)
        self.magicb.setText("Provide")

    def set_providing(self) -> None:
        self.state = AppState.UP
        self.process_state = ProcessState.PROVIDING
        self.app_up.emit()

        self.app_state_changed.emit()
        self.set_button_movie("red pulse.gif")
        self.profile.unkonfigure_button.setDisabled(False)
        self.profile.logout_button.setDisabled(False)
        self.magicb.setDisabled(False)
        self.magicb.setText("Cancel Provide..")

    def magic_button_clicked(self) -> None:
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

        if self.provide_future:
            if not self.provide_future.done():
                self.provide_future.cancel()
                self.set_unprovided()
                return
