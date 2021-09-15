from qtpy import QtWidgets
from abc import abstractmethod

class UIPortMixin:

    def __init__(self, *args, port = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.port = port


    @abstractmethod
    def get_current_value(self):
        """Gets the current value of the widget or returns None if
        no user input was set, or default

        Raises:
            NoValueSetError: An error that this widgets has no current value set
        """
        raise NotImplementedError("Please overwrite this in your Widget class")

class ErrorWidgetException(Exception):
    pass


class ErrorWidget(QtWidgets.QWidget, UIPortMixin):
    
    def __init__(self, *args, port, **kwargs) -> None:
        super().__init__(*args, port=port, **kwargs)
        self.build_ui()


    def build_ui(self):
        self.layout = QtWidgets.QVBoxLayout()
        self.searchBox = QtWidgets.QLineEdit(f"Error Widget for port {self.port.key} {self.port.typename} {self.port.widget.typename if self.port.widget else 'No widget provided'}")
        self.layout.addWidget(self.searchBox)
        self.setLayout(self.layout)

    def get_current_value(self):
        raise ErrorWidgetException("There was not Widget installed for this type")