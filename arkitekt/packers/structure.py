from abc import ABC, abstractclassmethod, abstractmethod
from typing import AbstractSet, Union

from pydantic.main import BaseModel

from arkitekt.schema.widgets import Widget


class StructureDefaults(BaseModel):
    widget: Widget


class Structure(ABC):
    """An Abstract Mixin to enforce packaging as a Structure before registering

    Args:
        ABC ([type]): [description]

    Raises:
        NotImplementedError: [description]
        NotImplementedError: [description]

    Returns:
        [type]: [description]
    """

    @abstractclassmethod
    def get_identifier(cls):
        raise NotImplementedError(
            "Every Structure needs to specify how to get its identifier"
        )

    @abstractclassmethod
    def get_defaults(cls) -> StructureDefaults:
        return StructureDefaults()

    @abstractclassmethod
    async def expand(cls, shrinked_value):
        raise NotImplementedError("Every Structure needs to implement a expand Method")

    @abstractmethod
    async def shrink(self):
        raise NotImplementedError("Every Structure needs to implement a shrink Method")
