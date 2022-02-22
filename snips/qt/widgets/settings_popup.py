from qtpy import QtWidgets


class SettingsPopup(QtWidgets.QDialog):
    def __init__(self, magic_bar, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.magic_bar = magic_bar

        self.magic_bar.agent.provide_signal.connect(self.set_delete_disabled)
        self.magic_bar.agent.provide_signal.connect(self.set_logout_disabled)
        self.magic_bar.agent.unprovide_signal.connect(self.set_logout_enabled)
        self.magic_bar.herre.login_signal.connect(self.set_delete_disabled)
        self.magic_bar.herre.logout_signal.connect(self.set_delete_enabled)

        self.layout = QtWidgets.QVBoxLayout()

        self.delete_fakts = QtWidgets.QPushButton("Delete Configuration")
        self.delete_fakts.clicked.connect(self.fakts_delete)

        self.logout_button = QtWidgets.QPushButton("Logout")
        self.logout_button.clicked.connect(self.logout_pressed)

        self.layout.addWidget(self.delete_fakts)
        self.layout.addWidget(self.logout_button)
        self.setLayout(self.layout)

    def set_delete_disabled(self):
        self.delete_fakts.setDisabled(True)

    def set_delete_enabled(self):
        self.delete_fakts.setDisabled(False)

    def set_logout_disabled(self):
        self.logout_button.setDisabled(True)

    def set_logout_enabled(self):
        self.logout_button.setDisabled(False)

    def fakts_delete(self):
        if self.magic_bar.fakts.loaded:
            self.magic_bar.fakts.delete()

    def logout_pressed(self):
        if self.magic_bar.herre.logged_in:
            self.magic_bar.herre.logout()
