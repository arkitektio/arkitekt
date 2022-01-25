from arkitekt.api.schema import WidgetInput


def SliderWidget(**kwargs):
    return WidgetInput(typename="SliderWidget", **kwargs)


def SearchWidget(**kwargs):
    return WidgetInput(typename="SearchWidget", **kwargs)
