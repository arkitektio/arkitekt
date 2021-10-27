from qtpy import QtWidgets, QtGui
from arkitekt.qt.images.dir import get_image_path
from arkitekt.qt.widgets.settings_popup import SettingsPopup
from fakts.qt import QtFakts
from herre.qt import QtHerre
from arkitekt.qt.agent import QtAgent
import traceback


class MagicBar(QtWidgets.QWidget):
    settingsPopupClass = SettingsPopup

    def __init__(self, fakts: QtFakts, herre: QtHerre, agent: QtAgent, *args, parent=None, darkMode=False, **kwargs) -> None:
        super().__init__(*args, parent=parent,**kwargs)

        self.darkMode = darkMode
        self.fakts = fakts
        self.herre = herre
        self.agent = agent

        self.fakts.loaded_signal.connect(self.on_facts_loaded)
        self.herre.login_signal.connect(self.on_herre_login)
        self.agent.provide_signal.connect(self.on_agent_provide)

        # Tasks 
        self.load_fakts_task = None
        self.herre_login_task = None
        self.agent_provide_task = None

        #Settings
        self.gear_button_popup = self.settingsPopupClass(self)


        self.magicb = QtWidgets.QPushButton("Connect")
        self.magicb.setMinimumHeight(30)
        self.magicb.setMaximumHeight(30)

        self.layout = QtWidgets.QHBoxLayout()
        self.gearb_pix = QtGui.QPixmap(get_image_path("gear.png", darkMode=darkMode))
        self.gearb = QtWidgets.QPushButton()
        self.gearb.setIcon(QtGui.QIcon(self.gearb_pix))
        self.gearb.setMinimumWidth(30)
        self.gearb.setMaximumWidth(30)
        self.gearb.setMinimumHeight(30)
        self.gearb.setMaximumHeight(30)


        self.layout.addWidget(self.magicb)
        self.layout.addWidget(self.gearb)
        self.setLayout(self.layout)


        self.magicb.clicked.connect(self.magic_button_clicked)
        self.gearb.clicked.connect(self.gear_button_clicked)



        if not self.fakts.loaded:
            self.set_unkonfigured()

        else:
            self.set_unconnected()


    def on_agent_except(self, exc_obj):
        self.set_halted()
        errorbox = QtWidgets.QMessageBox()
        errorbox.setText(''.join(traceback.format_exception(None, exc_obj, exc_obj.__traceback__)))
        errorbox.exec_()

    def on_fakts_except(self, exc_obj):
        self.set_unkonfigured()
        errorbox = QtWidgets.QMessageBox()
        errorbox.setText(''.join(traceback.format_exception(None, exc_obj, exc_obj.__traceback__)))
        errorbox.exec_()

    def on_herre_except(self, exc_obj):
        self.set_unconnected()
        errorbox = QtWidgets.QMessageBox()
        errorbox.setText(''.join(traceback.format_exception(None, exc_obj, exc_obj.__traceback__)))
        errorbox.exec_()


    def on_facts_loaded(self, konfik_state):
        if konfik_state:  self.set_unconnected()
        else: self.set_unkonfigured()
    
    def on_herre_login(self, login_state):
        if login_state: self.set_unprovided()
        else: self.set_unconnected()

    def on_agent_provide(self, provide_state):
        if provide_state: self.set_providing()
        else: self.set_halted()


    def gear_button_clicked(self):
        self.gear_button_popup.show()

    def magic_button_clicked(self):
        if not self.fakts.loaded:
            # App is not Konfigured Yet lets do this
            if self.load_fakts_task: 
                self.load_fakts_task.cancel()
                self.load_fakts_task = None

            self.load_fakts_task = self.fakts.load(as_task=True)
            self.load_fakts_task.except_signal.connect(self.on_fakts_except)
            return 

        if not self.herre.logged_in:
            if self.herre_login_task: 
                self.herre_login_task.cancel()
                self.herre_login_task = None

            self.herre_login_task = self.herre.login(as_task=True) 
            self.herre_login_task.except_signal.connect(self.on_herre_except) 
            return 

        if not self.agent_provide_task:
            self.agent_provide_task = self.agent.provide(as_task=True)
            self.agent_provide_task.except_signal.connect(self.on_agent_except)
            return
        
        else:
            self.agent_provide_task.cancel()
            self.agent_provide_task = None
            return 

        
    def update_movie(self):
        self.magicb.setIcon(QtGui.QIcon(self.magicb_movie.currentPixmap()))

    def set_unkonfigured(self):
        self.magicb_movie = QtGui.QMovie(get_image_path("pink pulse.gif", darkMode=self.darkMode))
        self.magicb_movie.frameChanged.connect(self.update_movie)
        self.magicb_movie.start()

        self.magicb.setText("Konfigure App")

    def set_unconnected(self):
        self.magicb_movie = QtGui.QMovie(get_image_path("green pulse.gif", darkMode=self.darkMode))
        self.magicb_movie.frameChanged.connect(self.update_movie)
        self.magicb_movie.start()

        self.magicb.setText("Connect")

    def set_halted(self):
        self.magicb_movie = QtGui.QMovie(get_image_path("orange pulse.gif", darkMode=self.darkMode))
        self.magicb_movie.frameChanged.connect(self.update_movie)
        self.magicb_movie.start()

        self.magicb.setText("Halted")

    def set_unprovided(self):
        self.magicb_movie = QtGui.QMovie(get_image_path("green pulse.gif", darkMode=self.darkMode))
        self.magicb_movie.frameChanged.connect(self.update_movie)
        self.magicb_movie.start()

        self.magicb.setText("Provide")

    def set_providing(self):
        self.magicb_movie = QtGui.QMovie(get_image_path("green pulse.gif", darkMode=self.darkMode))
        self.magicb_movie.frameChanged.connect(self.update_movie)
        self.magicb_movie.start()

        self.magicb.setText("Providing...")