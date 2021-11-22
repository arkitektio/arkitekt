from abc import ABC, abstractclassmethod, abstractmethod
from typing import AbstractSet, Union

from pydantic.main import BaseModel

from arkitekt.schema.widgets import Widget
from enum import Enum

class BoundType(str, Enum):
    GLOBAL = "GLOBAL"
    AGENT = "AGENT"
    REGISTRY = "REGISTRY"
    APP = "APP"



class StructureMeta(BaseModel):
    widget: Widget = None
    identifier: str
    bound: BoundType = BoundType.GLOBAL
    overwrite = False


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
    def get_structure_meta(cls) -> StructureMeta:
        return StructureMeta()

    @abstractclassmethod
    async def expand(cls, shrinked_value):
        raise NotImplementedError("Every Structure needs to implement a expand Method")

    @abstractmethod
    async def shrink(self):
        raise NotImplementedError("Every Structure needs to implement a shrink Method")
