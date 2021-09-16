from arkitekt.ui.registry import get_widget_registry
from typing import Type
from qtpy import QtWidgets
from arkitekt.ui.qtwidgets.base import UIPortMixin
from arkitekt.schema.ports import *
from herre.wards.graphql import ParsedQuery
from herre.access.model import GraphQLModel

registry = get_widget_registry()

class QueryOption(BaseModel):
    label: str
    value: str


@registry.register(
    [(ListArgPort, SearchWidget ),(ListKwargPort, SearchWidget)]
)
class QTListSearchWidget(QtWidgets.QWidget, UIPortMixin):
    port: ListArgPort

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.build_ui()
        self.selected_value = None
        self.child: StructureArgPort = self.port.child
        self.structure = get_packer_registry().get_structure(self.child.identifier)
        assert issubclass(self.structure, GraphQLModel), "Selected Port is not a GraphQL Model. Search widget will not work"


    def build_ui(self):
        self.layout = QtWidgets.QVBoxLayout()


        self.searchBox = QtWidgets.QLineEdit("")
        self.searchBox.textChanged.connect(self.update_list)

        self.listWidget = QtWidgets.QListWidget()
        self.listWidget.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection 
        )


        self.layout.addWidget(self.searchBox)
        self.layout.addWidget(self.listWidget)
        self.layout.addWidget(QtWidgets.QLabel(self.port.description))

        self.listWidget.itemClicked.connect(self.update_value)

        self.setLayout(self.layout)


    def update_list(self, searchString):
        if len(searchString) > 1:

            results = self.structure.objects.ward._run_sync(ParsedQuery(self.port.widget.query), {"search": searchString})
            self.options = [QueryOption(**values) for values in results["options"]]

            self.listWidget.clear()
            for option in self.options:
                item = QtWidgets.QListWidgetItem(option.label)
                self.listWidget.addItem(item)

    
    def update_value(self):
        items = self.listWidget.selectedIndexes()
        self.selected_value = [self.structure(id=self.options[index.row()].value) for index in items]


    def get_current_value(self):
        return self.selected_value 



