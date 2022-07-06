from arkitekt.api.schema import WidgetInput, ReturnWidgetInput


def SliderWidget(min=0, max=0):
    return WidgetInput(typename="SliderWidget", min=min, max=max)


def SearchWidget(query=""):
    return WidgetInput(typename="SearchWidget", query=query)


def ImageReturnWidget(query=""):
    return ReturnWidgetInput(typename="ImageReturnWidget", query=query)
