from enum import Enum
from qtpy import QtWidgets, QtGui, QtCore
from arkitekt.qt.types import QtApp
from koil.qt import async_to_qt

from arkitekt.app.app import App
from arkitekt.runtime import Runtime
from .utils import get_image_path
from typing import Any, Optional, Callable
import logging
import aiohttp
from fakts import Fakts
from fakts.grants.remote import RemoteGrant
from fakts.grants.remote.discovery.well_known import WellKnownDiscovery
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
                    logger.error(
                        f"Failed to download the image. Status code: {resp.status}"
                    )
                    return None


class _LogLines(QtCore.QObject):
    """The Qt side of :class:`ArkitektLogsRetriever`: carries a line to the widget's thread."""

    appendPlainText = QtCore.Signal(str)


class ArkitektLogsRetriever(logging.Handler):
    """A logging handler that will emit a Qt signal when a log message is received.

    It holds its QObject rather than being one: a class that is both a Handler and a
    QObject depends on each base's ``__init__`` being called by hand.
    """

    def __init__(self, widget: QtWidgets.QPlainTextEdit) -> None:
        """A logging handler that will emit a Qt signal when a log message is received.

        Parameters
        ----------
        widget : QtWidgets.QPlainTextEdit
            A plain text edit widget to display the logs in.
        """
        super().__init__()
        self.lines = _LogLines()
        self.lines.appendPlainText.connect(widget.appendPlainText)
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s"
            )
        )

    def emit(self, record: LogRecord) -> None:
        """Emit a Qt signal when a log message is received.

        The handler sits on the root logger, which outlives the widget. Once Qt has
        deleted the widget's side of it, it takes itself off instead of raising into
        whatever logged next.
        """
        msg = self.format(record)
        try:
            self.lines.appendPlainText.emit(msg)
        except RuntimeError:
            logging.getLogger().removeHandler(self)


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
        app: App[Any],
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
        # Configuration, not built state: a bar is built before its app is
        # entered, and `identifier`/`version`/`logo` answer from the moment the
        # app is configured -- which is all a title bar needs.
        identifier = self.app.identifier
        version = self.app.version

        self.settings = QtCore.QSettings(
            "arkitekt",
            f"{identifier}:{version}:profile",
        )

        self.setWindowTitle("Settings")

        self.infobar = QtWidgets.QVBoxLayout()

        self.mylayout = QtWidgets.QHBoxLayout()
        self.setLayout(self.mylayout)
        self.mylayout.addLayout(self.infobar)

        if self.app.logo:
            self.infobar.addWidget(Logo(self.app.logo, parent=self))

        self.infobar.addWidget(QtWidgets.QLabel(identifier))
        self.infobar.addWidget(QtWidgets.QLabel(version))

        self.unkonfigure_button = QtWidgets.QPushButton("Reconnect")
        self.unkonfigure_button.clicked.connect(self._reconnect)

        button_bar = QtWidgets.QHBoxLayout()
        self.infobar.addLayout(button_bar)
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

    def _reconnect(self) -> None:
        """Log in again: re-run the bar's refresh (the Reconnect button)."""
        self.bar.refresh_task.run()

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


class StatusDot(QtWidgets.QWidget):
    """A small coloured dot that says where the run stands, and breathes while it is live."""

    SIZE = 14

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        """A grey dot that stands still, until it is told a status."""
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self._color = QtGui.QColor("#94a3b8")
        self._phase = 0.0
        self._pulse = QtCore.QVariantAnimation(self)
        self._pulse.setStartValue(0.0)
        self._pulse.setEndValue(1.0)
        self._pulse.setDuration(1400)
        self._pulse.setLoopCount(-1)
        self._pulse.valueChanged.connect(self._on_phase)

    def set_status(self, color: str, pulsing: bool = False) -> None:
        """Show ``color``; a pulsing dot has a halo that grows and fades."""
        self._color = QtGui.QColor(color)
        if pulsing:
            self._pulse.start()
        else:
            self._pulse.stop()
            self._phase = 0.0
        self.update()

    @property
    def pulsing(self) -> bool:
        """Whether the dot is breathing."""
        return self._pulse.state() == QtCore.QAbstractAnimation.Running

    def _on_phase(self, value: Any) -> None:  # noqa: ANN401 -- a QVariant
        self._phase = float(value)
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802 -- Qt's name
        """Paint the dot, and around it the halo of a pulse."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        centre = QtCore.QPointF(self.width() / 2, self.height() / 2)
        core = self.SIZE * 0.29
        if self.pulsing:
            halo = QtGui.QColor(self._color)
            halo.setAlphaF(0.45 * (1.0 - self._phase))
            painter.setBrush(halo)
            radius = core + (self.SIZE / 2 - core) * self._phase
            painter.drawEllipse(centre, radius, radius)
        painter.setBrush(self._color)
        painter.drawEllipse(centre, core, core)
        painter.end()


#: The colour of the dot per step, and of the button that takes the next one.
STATUS_COLORS = {
    "unkonfigured": "#94a3b8",
    "unlogged": "#f59e0b",
    "unprovided": "#3b82f6",
    "providing": "#22c55e",
}
ACCENT = "#6366f1"
ACCENT_HOVER = "#7477f5"
ACCENT_PRESSED = "#4f52d8"


def bar_stylesheet(dark_mode: bool) -> str:
    """The look of the bar: one filled button for the next step, quiet everything else."""
    ink = "255, 255, 255" if dark_mode else "15, 23, 42"
    return f"""
    QPushButton#magicButton {{
        background-color: {ACCENT};
        color: white;
        border: 1px solid {ACCENT};
        border-radius: 6px;
        padding: 0 14px;
        font-weight: 600;
    }}
    QPushButton#magicButton:hover {{ background-color: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
    QPushButton#magicButton:pressed {{ background-color: {ACCENT_PRESSED}; border-color: {ACCENT_PRESSED}; }}
    QPushButton#magicButton:disabled {{
        background-color: rgba({ink}, 0.08);
        border-color: rgba({ink}, 0.08);
        color: rgba({ink}, 0.4);
    }}
    QPushButton#magicButton[quiet="true"] {{
        background-color: transparent;
        color: rgba({ink}, 0.85);
        border: 1px solid rgba({ink}, 0.25);
    }}
    QPushButton#magicButton[quiet="true"]:hover {{ background-color: rgba({ink}, 0.08); }}
    QPushButton#magicButton[quiet="true"]:pressed {{ background-color: rgba({ink}, 0.16); }}
    QPushButton#gearButton {{
        background-color: transparent;
        border: 1px solid rgba({ink}, 0.25);
        border-radius: 6px;
    }}
    QPushButton#gearButton:hover {{ background-color: rgba({ink}, 0.08); }}
    QPushButton#gearButton:pressed {{ background-color: rgba({ink}, 0.16); }}
    QLabel#magicCaption {{ color: rgba({ink}, 0.62); background: transparent; }}
    """


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
    HEIGHT = 32

    app_state_changed = QtCore.Signal()
    app_up = QtCore.Signal()
    app_down = QtCore.Signal()
    app_error = QtCore.Signal()
    state = AppState.DOWN
    process_state = ProcessState.UNKONFIGURED

    def __init__(
        self,
        runtime: Runtime[Any],
        dark_mode: bool = False,
        on_error: Optional[Callable[[Exception], None]] = None,
        context: Optional[Any] = None,
    ) -> None:
        """Magic bar Widget

        This widget is a small button widget, that can be used to configure, login and put the
        app in providing and non providing states.. It also has a gear button that opens the
        profile dialog, that can be used to adjust some parameters of the qt app.

        Parameters
        ----------
        runtime : Runtime
            The run of a (Qt) app to drive, as ``connect(app)`` returns it. Enter
            it before the bar is used; the bar configures, logs in and provides
            through it.
        dark_mode : bool, optional
            Should we use the dark mode, by default False
        on_error : Optional[Callable[[Exception], None]], optional
            And additinal callback if an error is raised, by default None
        context : Optional[Any], optional
            The app context the run is provided with, for an app that declares
            one (``QtApp(..., app_context=Window)``): an action annotated with
            the class is handed it. Typically the window the bar sits in.
        """
        super().__init__()
        self.runtime = runtime
        self.context = context
        self.app = runtime.app

        # assert isinstance(
        #     self.app.koil, QtPedanticKoil
        # ), f"Koil should be Qt Koil but is {type(self.app.koil)}"
        self.dark_mode = dark_mode

        self.profile = Profile(self.app, self, dark_mode=dark_mode)
        self.profile.updated.connect(self.on_profile_updated)

        # Every task below goes through a wrapper method rather than binding
        # `runtime.fakts.<x>` here: a bar may be built before its runtime is
        # entered, so fakts and the agent do not exist yet. Resolving them when
        # the button is pressed is both correct and the only thing that works --
        # `async_to_qt` wants a real coroutine function, so these cannot be lambdas.

        self.configure_task = async_to_qt(self._aload)
        self.configure_task.errored.connect(self.configure_errored)
        self.configure_task.returned.connect(self.set_unlogined)

        self.refresh_task = async_to_qt(self._arefresh)
        self.refresh_task.errored.connect(self.configure_errored)
        self.refresh_task.returned.connect(self.set_unlogined)

        self.get_token_task = async_to_qt(self._aget_token)
        self.get_token_task.errored.connect(self.login_errored)
        self.get_token_task.returned.connect(self.set_unprovided)

        self.refresh_token_task = async_to_qt(self._arefresh_token)
        self.refresh_token_task.errored.connect(self.login_errored)
        self.refresh_token_task.returned.connect(self.set_unprovided)

        self.provide_task = async_to_qt(self._aprovide)
        self.provide_task.errored.connect(self.provide_errored)
        self.provide_task.returned.connect(self.set_unprovided)

        self.magicb = QtWidgets.QPushButton(MagicBar.CONNECT_LABEL)
        self.magicb.setObjectName("magicButton")
        self.magicb.setFixedHeight(self.HEIGHT)
        self.magicb.setCursor(QtCore.Qt.PointingHandCursor)
        self.magicb.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.configure_future = None
        self.login_future = None
        self.provide_future = None

        self.gearb = QtWidgets.QPushButton()
        self.gearb.setObjectName("gearButton")
        self.gearb.setIcon(QtGui.QIcon(QtGui.QPixmap(get_image_path("gear.png", dark_mode=dark_mode))))
        self.gearb.setIconSize(QtCore.QSize(16, 16))
        self.gearb.setFixedSize(self.HEIGHT, self.HEIGHT)
        self.gearb.setCursor(QtCore.Qt.PointingHandCursor)
        self.gearb.setToolTip("Settings and logs")
        self._on_error = on_error

        self.magicb.clicked.connect(self.magic_button_clicked)
        self.gearb.clicked.connect(self.gear_button_clicked)

        # Under the buttons: where the run stands, in a dot and a few words.
        self.dot = StatusDot()
        self.caption = QtWidgets.QLabel()
        self.caption.setObjectName("magicCaption")
        # Never the reason a dock grows: a long server name is cut, not the dock widened.
        self.caption.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        caption_font = self.caption.font()
        caption_font.setPointSizeF(max(caption_font.pointSizeF() - 1.0, 7.0))
        self.caption.setFont(caption_font)

        buttons = QtWidgets.QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(6)
        buttons.addWidget(self.magicb)
        buttons.addWidget(self.gearb)

        status = QtWidgets.QHBoxLayout()
        status.setContentsMargins(2, 0, 0, 0)
        status.setSpacing(6)
        status.addWidget(self.dot)
        status.addWidget(self.caption, 1)

        self.mylayout = QtWidgets.QVBoxLayout()
        self.mylayout.setContentsMargins(0, 0, 0, 0)
        self.mylayout.setSpacing(6)
        self.mylayout.addLayout(buttons)
        self.mylayout.addLayout(status)
        self.setLayout(self.mylayout)
        self.setStyleSheet(bar_stylesheet(dark_mode))

        self.set_unkonfigured()
        self.on_profile_updated()

    def on_profile_updated(self) -> None:
        """Callback for when the profile is updated."""
        if self.profile.go_all_the_way_down:
            self.set_unprovided()

    def show_error(self, ex: BaseException) -> None:
        """Show an error message

        Parameters
        ----------
        ex : BaseException
            The exception to show.
        """
        if not isinstance(ex, Exception):
            # A cancelled task (CancelledError and the like) ended; it did not fail.
            logger.info(f"Task ended: {ex!r}")
            return
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

    def configure_errored(self, ex: BaseException) -> None:
        self.set_unkonfigured()
        self.show_error(ex)

    def login_errored(self, ex: BaseException) -> None:
        self.set_unlogined()
        self.show_error(ex)

    def provide_errored(self, ex: BaseException) -> None:
        self.set_unprovided()
        self.show_error(ex)

    def on_configured(self) -> None:
        self.magicb.setText("Log in")

    def on_login(self) -> None:
        self.magicb.setText("Provide")

    def on_provided(self) -> None:
        self.magicb.setText("Provide ended")

    def on_providing_ended(self) -> None:
        pass

    def gear_button_clicked(self) -> None:
        self.profile.show()

    def server_name(self) -> Optional[str]:
        """The server this run is configured for, without its scheme; None before it has one."""
        discovery = self._well_known()
        url = discovery.url if discovery is not None else None
        if not url:
            return None
        return str(url).split("://", 1)[-1].rstrip("/")

    def _present(self, label: str, caption: str, quiet: bool = False, pulsing: bool = False) -> None:
        """Show a step: what the button does next, and where the run stands.

        Args:
            label: The button's text: the next step.
            caption: The line under it. ``{server}`` is replaced by the server's name.
            quiet: An outlined button, for a step that ends something rather than starts it.
            pulsing: Whether the dot breathes: the run is live.
        """
        server = self.server_name()
        text = caption.format(server=server) if server else caption.split(" on {server}")[0]
        self.magicb.setText(label)
        self.magicb.setDisabled(False)
        if self.magicb.property("quiet") != quiet:
            self.magicb.setProperty("quiet", quiet)
            # A property a selector reads only takes effect on a re-polish.
            self.magicb.style().unpolish(self.magicb)
            self.magicb.style().polish(self.magicb)
        self.dot.set_status(STATUS_COLORS[self.process_state.value], pulsing=pulsing)
        self.caption.setText(text)
        self.caption.setToolTip(text)

    def set_unkonfigured(self) -> None:
        self.state = AppState.DOWN
        self.process_state = ProcessState.UNKONFIGURED
        self.app_down.emit()
        self.app_state_changed.emit()
        self.profile.unkonfigure_button.setDisabled(True)
        self._present(MagicBar.CONNECT_LABEL, "Not connected")
        self.magicb.setToolTip("Choose the server to connect to")

    def set_unlogined(self, _result: object = None) -> None:
        self.state = AppState.DOWN
        self.process_state = ProcessState.UNLOGGED
        self.app_down.emit()

        self.app_state_changed.emit()
        self.profile.unkonfigure_button.setDisabled(False)
        self._present("Log in", "Not logged in on {server}")
        self.magicb.setToolTip("Log in to the server")

    def set_unprovided(self, _result: object = None) -> None:
        self.state = AppState.UP
        self.process_state = ProcessState.UNPROVIDED
        self.app_up.emit()

        self.app_state_changed.emit()
        self.profile.unkonfigure_button.setDisabled(False)
        self._present("Provide", "Ready on {server}")
        self.magicb.setToolTip("Offer this app's actions to the server")

    def set_providing(self) -> None:
        self.state = AppState.UP
        self.process_state = ProcessState.PROVIDING
        self.app_up.emit()

        self.app_state_changed.emit()
        self.profile.unkonfigure_button.setDisabled(False)
        self._present("Stop providing", "Providing on {server}", quiet=True, pulsing=True)
        self.magicb.setToolTip("Stop offering this app's actions")

    def get_endpoints(self) -> list[str]:
        settings = QtCore.QSettings("arkitekt", "magic_bar")
        history = settings.value("history", [], type=list)
        # Ensure they are strings
        history = [str(h) for h in history]

        defaults = ["go.arkitekt.live", "http://127.0.0.1:8000"]
        discovery = self._well_known()
        if discovery is not None and discovery.url:
            defaults.insert(0, discovery.url)

        # Merge and deduplicate
        all_endpoints = []
        seen = set()
        for e in history + defaults:
            if e not in seen:
                all_endpoints.append(e)
                seen.add(e)
        return all_endpoints

    def add_to_history(self, url: str) -> None:
        settings = QtCore.QSettings("arkitekt", "magic_bar")
        history = settings.value("history", [], type=list)
        history = [str(h) for h in history]
        if url in history:
            history.remove(url)
        history.insert(0, url)
        settings.setValue("history", history)

    def connect_to_endpoint(self, url: str) -> None:
        discovery = self._well_known()
        if discovery is None:
            logger.error("Could not update the fakts url: this run does not discover its server")
        else:
            discovery.url = url

        self.add_to_history(url)
        self.configure_task.run()

    def show_endpoints_menu(self) -> None:
        menu = QtWidgets.QMenu(self)

        endpoints = self.get_endpoints()

        for endpoint in endpoints:
            action = menu.addAction(endpoint)
            if action is None:
                continue
            action.triggered.connect(
                lambda checked, e=endpoint: self.connect_to_endpoint(e)
            )

        menu.exec_(self.magicb.mapToGlobal(QtCore.QPoint(0, self.magicb.height())))

    def magic_button_clicked(self) -> None:
        if self.process_state == ProcessState.UNKONFIGURED:
            self.show_endpoints_menu()
            return

        if (
            self.process_state == ProcessState.UNLOGGED
            and not self.profile.go_all_the_way_down
        ):
            if not self.login_future or self.login_future.done():
                self.login_future = self.get_token_task.run()
                self.magicb.setText("Cancel login")
                return
            if not self.login_future.done():
                self.login_future.cancel()
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

    # ------------------------------------------------------------------ #
    # Built state, resolved when the button is pressed                   #
    # ------------------------------------------------------------------ #
    # A magic bar may be constructed before its runtime is entered, so fakts
    # and the agent do not exist yet. These wrappers are what the tasks
    # above are built from: real coroutine functions (`async_to_qt` requires
    # one), each reaching for the app's built parts at the moment it runs.

    def _fakts(self) -> Fakts:
        """The run's fakts, which exist once its runtime is entered."""
        fakts = self.runtime.fakts
        if fakts is None:
            raise RuntimeError(
                "This app's runtime has no fakts: it is not entered yet, or the app "
                "needs no service and so authenticates nothing."
            )
        return fakts

    def _well_known(self) -> WellKnownDiscovery | None:
        """How the run finds its server, when it is by url (the only way arkitekt builds)."""
        fakts = self.runtime.fakts
        grant = fakts.grant if fakts is not None else None
        if isinstance(grant, RemoteGrant) and isinstance(grant.discovery, WellKnownDiscovery):
            return grant.discovery
        return None

    async def _aload(self) -> Any:
        return await self._fakts().aload()

    async def _arefresh(self) -> Any:
        return await self._fakts().arefresh()

    async def _aget_token(self) -> Any:
        return await self._fakts().aget_token()

    async def _arefresh_token(self) -> Any:
        return await self._fakts().arefresh_token()

    async def _aprovide(self) -> Any:
        # Through the runtime: it owns the agent, binds it to this run and
        # applies the run's options (force) before providing.
        return await self.runtime.arun(self.context)
