from qtpy import QtCore, QtGui
from qtpy import QtWidgets
from arkitekt.agents.base import Agent
from arkitekt.qt.agent import QtAgent
from arkitekt.messages.postman.provide.bounced_provide import BouncedProvideMessage
from arkitekt.schema.template import Template


class ProvisionDetailWidget(QtWidgets.QWidget):
    def __init__(
        self, provide: BouncedProvideMessage, agent: Agent, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        template: Template = agent.templateTemplatesMap[provide.data.template]
        self.layout = QtWidgets.QVBoxLayout()

        name = QtWidgets.QLabel(template.node.name)
        name.setFont(QtGui.QFont("Arial", 16))

        identifier = QtWidgets.QLabel(
            f"@{template.node.package}/{template.node.interface}"
        )
        identifier.setFont(QtGui.QFont("Arial", 10))

        description = QtWidgets.QLabel(template.node.description)
        description.setWordWrap(True)

        self.layout.addWidget(name)
        self.layout.addWidget(identifier)
        self.layout.addWidget(description)
        self.setLayout(self.layout)


class ProvisionListWidget(QtWidgets.QWidget):
    def __init__(
        self, provide: BouncedProvideMessage, agent: Agent, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        template: Template = agent.templateTemplatesMap[provide.data.template]
        self.provide = provide
        self.agent = agent

        self.row = QtWidgets.QHBoxLayout()

        left = QtWidgets.QWidget()
        leftlayout = QtWidgets.QVBoxLayout()

        self.dialog = ProvisionDetailWidget(self.provide, self.agent)

        node_label = QtWidgets.QLabel(template.node.name)
        node_label.setFont(QtGui.QFont("Arial", 10))

        context_label = QtWidgets.QLabel(provide.meta.context.user)
        context_label.setFont(QtGui.QFont("Arial", 8))

        leftlayout.addWidget(node_label)
        leftlayout.addWidget(context_label)

        left.setLayout(leftlayout)

        open_button = QtWidgets.QToolButton()
        open_button.clicked.connect(self.open_provision)

        self.row.addWidget(left)
        self.row.addWidget(open_button, alignment=QtCore.Qt.AlignRight)

        self.setLayout(self.row)

    def open_provision(self):
        self.dialog.show()


class ProvisionsWidget(QtWidgets.QWidget):
    def __init__(self, qt_agent: QtAgent = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.agent = qt_agent
        self.layout = QtWidgets.QVBoxLayout()
        self.listWidget = QtWidgets.QListWidget()
        self.layout.addWidget(self.listWidget)

        self.setLayout(self.layout)
        self.provisions = {}

        self.agent.provision_signal.connect(self.provision_in)

    def provision_in(self, provide: BouncedProvideMessage):
        self.provisions[provide.meta.reference] = provide

        self.listWidget.clear()
        for key, provide in self.provisions.items():
            item = QtWidgets.QListWidgetItem()
            w = ProvisionListWidget(provide, self.agent)
            item.setSizeHint(w.minimumSizeHint())
            self.listWidget.addItem(item)
            self.listWidget.setItemWidget(item, w)
