from pydantic.main import BaseModel
from arkitekt.packers.registry import (
    StructureMeta,
    register_structure,
)


@register_structure(meta=StructureMeta(identifier="test"))
class SerializableObject(BaseModel):
    number: int

    async def shrink(self):
        return self.number

    @classmethod
    async def expand(cls, shrinked_value):
        return cls(number=shrinked_value)


@register_structure(meta=StructureMeta(identifier="karl"))
class SecondSerializableObject:
    async def shrink(self):
        return 5

    @classmethod
    async def expand(cls, shrinked_value):
        return cls()
