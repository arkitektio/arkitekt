from qtpy import QtWidgets


class SettingsPopup(QtWidgets.QDialog):
    def __init__(self, magic_bar, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.magic_bar = magic_bar

        self.layout = QtWidgets.QVBoxLayout()

        self.delete_fakts = QtWidgets.QPushButton("Delete Configuration")
        self.delete_fakts.clicked.connect(self.fakts_delete)

        self.logout_button = QtWidgets.QPushButton("Logout")
        self.logout_button.clicked.connect(self.logout_pressed)

        self.layout.addWidget(self.delete_fakts)
        self.layout.addWidget(self.logout_button)
        self.setLayout(self.layout)

    def fakts_delete(self):
        self.magic_bar.fakts.delete()


    def logout_pressed(self):
        self.magic_bar.herre.logout()
