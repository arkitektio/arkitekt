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
    BsxWidget,
    ChoiceReturnWidget,
    ChoiceWidget,
    CustomReturnWidget,
    CustomWidget,
    ParagraphWidget,
    ProxyWidget,
    SearchWidget,
    SliderWidget,
    StringWidget,
    StructurePicker,
    withChoices,
    withEffect,
    withStateChoices,
    withValidator,
)

__all__ = [
    "BsxWidget",
    "ChoiceAssignWidgetInput",
    "ChoiceReturnWidget",
    "ChoiceReturnWidgetInput",
    "ChoiceWidget",
    "CustomAssignWidgetInput",
    "CustomReturnWidget",
    "CustomReturnWidgetInput",
    "CustomWidget",
    "ParagraphWidget",
    "ProxyAssignWidgetInput",
    "ProxyWidget",
    "SearchAssignWidgetInput",
    "SearchWidget",
    "SliderAssignWidgetInput",
    "SliderWidget",
    "StateChoiceAssignWidgetInput",
    "StringAssignWidgetInput",
    "StringWidget",
    "StructurePicker",
    "withChoices",
    "withEffect",
    "withStateChoices",
    "withValidator",
]
