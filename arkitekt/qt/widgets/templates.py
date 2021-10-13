from PyQt5 import QtCore
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QListWidgetItem, QPushButton, QToolButton, QWidget
from qtpy import QtWidgets
from arkitekt.agents.base import Agent
from arkitekt.agents.qt import QtAgent
from arkitekt.config import ArkitektConfig
from arkitekt.messages.postman.provide.bounced_provide import BouncedProvideMessage
from arkitekt.schema.template import Template
import webbrowser

def open_in_arkitekt(path):
    config = ArkitektConfig.from_konfik()
    webbrowser.open(f"http://{config.host}:3000{path}")



class PortsWrapped(QtWidgets.QWidget):

    def __init__(self, ports, title, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = QtWidgets.QVBoxLayout()
        self.formGroupBox = QtWidgets.QGroupBox(title)
        qlayout = QtWidgets.QFormLayout()

        for port in ports:
            argLabel = QLabel(port.typename + " | " + port.key)
            argDescription = QLabel(port.description)
            argDescription.setFont(QFont("Arial", 8))
            qlayout.addWidget(argLabel)
            qlayout.addWidget(argDescription)

        
        self.formGroupBox.setLayout(qlayout)
        self.layout.addWidget(self.formGroupBox)
        self.setLayout(self.layout)







class TemplateDetailWidget(QtWidgets.QWidget):

    def __init__(self, template: Template, agent: Agent, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.template = template
        self.layout = QtWidgets.QVBoxLayout()

        name = QLabel(template.node.name)
        name.setFont(QFont("Arial", 16))

        identifier = QLabel(f"@{template.node.package}/{template.node.interface}")
        identifier.setFont(QFont("Arial", 10))

        description = QLabel(template.node.description)
        description.setWordWrap(True)

        open_button = QtWidgets.QPushButton("Open in Arkitekt")
        open_button.clicked.connect(self.open_in_arkitekt)



        self.layout.addWidget(name)
        self.layout.addWidget(identifier)
        self.layout.addWidget(description)


        self.layout.addWidget(PortsWrapped(template.node.args, "Arguments"))
        self.layout.addWidget(PortsWrapped(template.node.kwargs, "Constants"))
        self.layout.addWidget(PortsWrapped(template.node.returns, "Returns"))

        for kwarg in template.node.kwargs:
            kwargLabel = QLabel(kwarg.typename + " | " + kwarg.key + " | " + str(kwarg.default))
            self.layout.addWidget(kwargLabel)



        self.layout.addWidget(open_button)
        self.setLayout(self.layout)

    def open_in_arkitekt(self):
        open_in_arkitekt(f"/node/{self.template.node.id}")






class TemplatesListItemWidget(QtWidgets.QWidget):

    def __init__(self, template: Template, agent: Agent, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.template = template
        self.agent = agent

        self.row = QtWidgets.QHBoxLayout()

        left = QtWidgets.QWidget()
        leftlayout = QtWidgets.QVBoxLayout()

        self.dialog = TemplateDetailWidget(self.template, self.agent)


        node_label = QLabel(template.node.name)
        node_label.setFont(QFont("Arial", 10))

        context_label = QLabel(f"@{template.node.package}/{template.node.interface}")
        context_label.setFont(QFont("Arial", 8))

        leftlayout.addWidget(node_label)
        leftlayout.addWidget(context_label)

        left.setLayout(leftlayout)

        open_button = QToolButton()
        open_button.clicked.connect(self.open_provision)

        self.row.addWidget(left)
        self.row.addWidget(open_button,  alignment=QtCore.Qt.AlignRight)

        self.setLayout(self.row)

    def open_provision(self):
        self.dialog.show()




class TemplatesWidget(QtWidgets.QWidget):

    def __init__(self, qt_agent: QtAgent = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.agent = qt_agent
        self.layout = QtWidgets.QVBoxLayout()
        self.listWidget = QtWidgets.QListWidget()
        self.layout.addWidget(self.listWidget)


        self.agent.provide_signal.connect(self.on_provide)

        self.setLayout(self.layout)
        self.provisions = {}


    def on_provide(self, provide_state):
        print("Hidden Here")
        if provide_state:
            self.listWidget.clear()
            for key, template in self.agent.templateTemplatesMap.items():
                item = QListWidgetItem()
                w = TemplatesListItemWidget(template, self.agent)
                item.setSizeHint(w.minimumSizeHint())
                self.listWidget.addItem(item)
                self.listWidget.setItemWidget(item, w)

        else:
            self.listWidget.clear()
