

from herre.access.object import GraphQLObject
from typing import List, Optional, Union


class Widget(GraphQLObject):
    dependencies: Optional[List[str]]

    def _repr_html_list(self):
        return f"""
        <div class="container" style="border:1px solid #00000f;padding: 4px;">
            <div class="item item-1 font-xl">{self.__class__.__name__}</div>
        </div>
        """

class ValueWidget(Widget):
    pass


class QueryWidget(Widget):
    query: Optional[str]
    list: Optional[bool]


class SearchWidget(Widget):
    query: Optional[str]

class IntWidget(Widget):
    pass

class SliderWidget(Widget):
    """ A Slider widget enables
    a slider from min to max with
    equally spaced ticks.
    Please assert default is within
    the minimum and maximum

    Args:
        max(int): The Maximum Value for this Slider
        min(int): The Minimum Value for this Slider
    """
    min: Optional[int]
    max: Optional[int]


AllWidgets = Union[SearchWidget, IntWidget, SliderWidget, QueryWidget, ValueWidget]