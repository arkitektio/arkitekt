"""The widgets an action's ports may declare, and the widget models they build.

    from arkitekt.widgets import SearchWidget, withStateChoices
"""

from arkitekt_spec.actions import (
    BlokAssignWidgetInput,
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
    PortBlok,
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
    "BlokAssignWidgetInput",
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
    "PortBlok",
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
