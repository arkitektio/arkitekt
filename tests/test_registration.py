from arkitekt.structures.registry import (
    StructureDefinitionError,
    StructureRegistry,
    register,
    StructureOverwriteError,
)
import pytest


async def test_structure_registration():
    registry = StructureRegistry(allow_overwrites=False)

    @register(identifier="test", registry=registry)
    class SerializableObject:
        def __init__(self, number) -> None:
            super().__init__()
            self.number = number

        async def shrink(self):
            return self.number

        @classmethod
        async def expand(cls, shrinked_value):
            return cls(shrinked_value)

    assert "test" in registry.identifier_structure_map, "Registration fails"
    assert "test" in registry.identifier_expander_map, "Registration of expand failed"
    assert (
        SerializableObject.expand == registry.identifier_expander_map["test"]
    ), "Is not the same instance"

    with pytest.raises(StructureOverwriteError):

        @register(identifier="test", registry=registry)
        class SerializableObject:
            def __init__(self, number) -> None:
                super().__init__()
                self.number = number

            async def shrink(self):
                return self.number

            @classmethod
            async def expand(cls, shrinked_value):
                return cls(shrinked_value)

    with pytest.raises(StructureDefinitionError):

        @register(identifier="karl", registry=registry)
        class SerializableObject:
            def __init__(self, number) -> None:
                super().__init__()
                self.number = number

            @classmethod
            async def expand(cls, shrinked_value):
                return cls(shrinked_value)
