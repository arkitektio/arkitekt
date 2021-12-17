from pydantic.main import BaseModel
from arkitekt.packers.structure import Structure
from arkitekt.packers.registry import (
    PackerRegistry,
    StructureOverwriteError,
    UnpackableError,
    StructureMeta,
    register_structure,
)
from arkitekt.schema.ports import (
    DictArgPort,
    IntArgPort,
    ListArgPort,
    ListReturnPort,
    StringArgPort,
    StringKwargPort,
)
from typing import Dict, List, Tuple
from arkitekt.packers.utils import ShrinkingError, expand_outputs
from arkitekt.schema.node import Node
from arkitekt.packers import shrink_inputs, expand_inputs
from arkitekt.actors import define
import pytest


async def test_structure_registration():
    registry = PackerRegistry()

    @register_structure(meta=StructureMeta(identifier="test"), registry=registry)
    class SerializableObject:
        def __init__(self, number) -> None:
            super().__init__()
            self.number = number

        async def shrink(self):
            return self.number

        @classmethod
        async def expand(cls, shrinked_value):
            return cls(shrinked_value)

    assert "test" in registry.identifierStructureMap, "Registration fails"

    with pytest.raises(StructureOverwriteError):

        @register_structure(meta=StructureMeta(identifier="test"), registry=registry)
        class SerializableObject:
            def __init__(self, number) -> None:
                super().__init__()
                self.number = number

            async def shrink(self):
                return self.number

            @classmethod
            async def expand(cls, shrinked_value):
                return cls(shrinked_value)

    with pytest.raises(UnpackableError):

        @register_structure(meta=StructureMeta(identifier="karl"), registry=registry)
        class SerializableObject:
            def __init__(self, number) -> None:
                super().__init__()
                self.number = number

            @classmethod
            async def expand(cls, shrinked_value):
                return cls(shrinked_value)
