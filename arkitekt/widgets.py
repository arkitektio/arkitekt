from arkitekt.api.schema import WidgetInput


def SliderWidget(min=0, max=0):
    return WidgetInput(typename="SliderWidget", min=0, max=0)


def SearchWidget(query=""):
    return WidgetInput(typename="SearchWidget", query=query)
