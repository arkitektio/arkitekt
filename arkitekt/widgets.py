"""The widgets an action's ports may declare, and the widget models they build.

    from arkitekt.widgets import SearchWidget, withStateChoices
"""

from arkitekt_spec.actions import (
    ChoiceAssignWidgetInput,
    ChoiceReturnWidgetInput,
    CustomAssignWidgetInput,
    CustomReturnWidgetInput,
    ProxyAssignWidgetInput,
    SearchAssignWidgetInput,
    SliderAssignWidgetInput,
    StateChoiceAssignWidgetInput,
    StringAssignWidgetInput,
)
from arkitekt_spec.declare.widgets import (
    ChoiceReturnWidget,
    ChoiceWidget,
    CustomReturnWidget,
    CustomWidget,
    ParagraphWidget,
    ProxyWidget,
    SearchWidget,
    SliderWidget,
    StringWidget,
    withChoices,
    withEffect,
    withStateChoices,
    withValidator,
)

__all__ = [
    "ChoiceAssignWidgetInput",
    "ChoiceReturnWidgetInput",
    "CustomAssignWidgetInput",
    "CustomReturnWidgetInput",
    "ProxyAssignWidgetInput",
    "SearchAssignWidgetInput",
    "SliderAssignWidgetInput",
    "StateChoiceAssignWidgetInput",
    "StringAssignWidgetInput",
    "ChoiceReturnWidget",
    "ChoiceWidget",
    "CustomReturnWidget",
    "CustomWidget",
    "ParagraphWidget",
    "ProxyWidget",
    "SearchWidget",
    "SliderWidget",
    "StringWidget",
    "withChoices",
    "withEffect",
    "withStateChoices",
    "withValidator",
]
