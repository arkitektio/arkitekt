from arkitekt.schema.widgets import Widget
from arkitekt.schema.ports import Port
from typing import List

class NoWidgetRegisteredError(Exception):
    pass


class WidgetRegistry:

    def __init__(self) -> None:
        self.portTypeWidgetTypeQTWidgetMap = {}


    def get_widget_class(self, portType, widgetType):
        portType = portType.__class__.__name__ if isinstance(portType, Port) else portType
        widgetType = widgetType.typename if isinstance(widgetType, Widget) else widgetType
        try:
            return self.portTypeWidgetTypeQTWidgetMap[portType][widgetType]
        except KeyError as e:
            raise NoWidgetRegisteredError(f"No widget registered for {portType} and {widgetType}") from e


    def register_defaults(self):
        from arkitekt.ui.qtwidgets.qtlistsearchwidget import QTListSearchWidget
        from arkitekt.ui.qtwidgets.qtsliderwidget import QTSliderWidget

    def register(self, list: List):

        def register(widget_class):
            for pair in list:
                portType, widgetType = pair
                try:
                    portType = portType.__name__ if issubclass(portType, Port) else portType
                except:
                    portType = portType
                try:
                    widgetType = widgetType.__name__ if issubclass(widgetType, Widget) else widgetType
                except:
                    widgetType = widgetType
                self.portTypeWidgetTypeQTWidgetMap.setdefault(portType, {})[widgetType] = widget_class
            
            return widget_class


        return register


WIDGET_REGISTRY = None

def get_widget_registry(register_defaults=True):
    global WIDGET_REGISTRY
    if WIDGET_REGISTRY is None:
        WIDGET_REGISTRY = WidgetRegistry()
        if register_defaults: WIDGET_REGISTRY.register_defaults()

    return WIDGET_REGISTRY
