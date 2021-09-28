from abc import abstractmethod
from arkitekt.ui.qtwidgets.base import UIPortMixin

from pydantic.main import BaseModel
from arkitekt.packers.registry import get_packer_registry
from re import search
from typing import Any, Generic, Type, TypeVar
from arkitekt.schema.ports import ArgPort, KwargPort, ListArgPort, ListKwargPort, Port, StructureArgPort, StructureKwargPort
from arkitekt.schema.widgets import SearchWidget
from qtpy import QtWidgets
from arkitekt.schema.node import Node
from itertools import zip_longest
from typing import Generic
from arkitekt.ui.registry import get_widget_registry




def build_qtwidget_for_argport(port: ArgPort):
    qtwidgetClass = get_widget_registry().get_widget_class(port.typename, port.widget.typename)
    return qtwidgetClass(port=port)

def build_qtwidget_for_kwargport(port: KwargPort):
    qtwidgetClass = get_widget_registry().get_widget_class(port.typename, port.widget.typename)
    return qtwidgetClass(port=port)



class AssignWidget(QtWidgets.QDialog):

    def __init__(self, *args, node: Node = None, set_args = [], set_kwargs={}, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        assert node is not None, "Provide the node Parameter to use the assign widget"
        self.node = node
        self.set_args = set_args
        self.set_kwargs = set_kwargs
        self.populated_args = []
        self.populated_kwargs = {}
        self.args_kwargs_tuple = ([],{})


        assert len(self.set_args) <= len(self.node.args), "Was provided more Args than node accepts"

        

        self.build_ui()

    def build_args_widget(self):
        self.argsWidget = QtWidgets.QGroupBox("Args")
        self.argsLayout = QtWidgets.QFormLayout()

        for arg, port in zip_longest(self.set_args, self.node.args):
            if arg: 
                self.populated_args.append(arg)
            else:
                widget = build_qtwidget_for_argport(port)
                self.argsLayout.addRow(QtWidgets.QLabel(parent=self, text=port.label or port.key), widget)
                self.populated_args.append(widget)

        self.argsWidget.setLayout(self.argsLayout)
        return self.argsWidget

    def build_kwargs_widget(self):
        self.kwargsWidget = QtWidgets.QGroupBox("Kwargs")
        self.kwargsLayout = QtWidgets.QFormLayout()

        for port in self.node.kwargs:
            if port.key in self.set_kwargs: 
                self.populated_kwargs[port.key] = self.set_kwargs[port.key]
            else:
                widget = build_qtwidget_for_kwargport(port)
                self.kwargsLayout.addRow(QtWidgets.QLabel(parent=self, text=port.label or port.key), widget)
                self.populated_kwargs[port.key] = widget

        self.kwargsWidget.setLayout(self.kwargsLayout)
        return self.kwargsWidget
            
                # Arg is not Set so we have to build a widget


    def build_ui(self):

        self.setWindowTitle(f"Assigning to {self.node.name} : {self.node.package}/{self.node.interface}")

        self.layout = QtWidgets.QVBoxLayout()

        self.node_description =  QtWidgets.QLabel(self.node.description)

        self.argsWidget = self.build_args_widget()
        self.kwargsWidget = self.build_kwargs_widget()


        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.on_accept)
        self.buttonBox.rejected.connect(self.on_reject)

        self.layout.addWidget(self.node_description)
        self.layout.addWidget(self.argsWidget)
        self.layout.addWidget(self.kwargsWidget)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


    def on_accept(self):
        done_args = []

        for arg in self.populated_args:
            if isinstance(arg, UIPortMixin):
                done_args.append(arg.get_current_value())
            else:
                done_args.append(arg)
                    

        done_kwargs = {}

        for key, kwarg in self.populated_kwargs.items():
            if isinstance(kwarg, UIPortMixin):
                done_kwargs[key] = kwarg.get_current_value()
            else:
                done_kwargs[key] = kwarg


        self.args_kwargs_tuple = (done_args, done_kwargs)
        self.accept()
        self.close()


    def on_reject(self):
        self.args_kwargs_tuple = ([], {})
        self.accept()
        self.close()






