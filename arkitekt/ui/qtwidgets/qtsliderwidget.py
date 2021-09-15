from arkitekt.ui.registry import get_widget_registry
from typing import Type
from qtpy import QtWidgets, QtCore
from arkitekt.ui.qtwidgets.base import UIPortMixin
from arkitekt.schema.ports import *
from herre.wards.graphql import ParsedQuery

registry = get_widget_registry()


@registry.register(
    [(IntArgPort, SliderWidget ), (IntKwargPort, SliderWidget)]
)
class QTSliderWidget(QtWidgets.QWidget, UIPortMixin):
    port: IntKwargPort

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.selected_value = None
        self.widget: SliderWidget = self.port.widget

        self.build_ui()

    def build_ui(self):
        self.layout = QtWidgets.QVBoxLayout()

        self.sl = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.sl.setMinimum(self.widget.min or 0)
        self.sl.setMaximum(self.widget.max or 100)
        self.sl.setValue(self.port.default if isinstance(self.port, IntKwargPort) else 0)
        self.sl.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.sl.setTickInterval(5)


        self.layout.addWidget(self.sl)
        self.layout.addWidget(QtWidgets.QLabel(self.port.description))
        self.setLayout(self.layout)


    def get_current_value(self):
        return self.sl.value()



