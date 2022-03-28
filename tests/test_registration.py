from arkitekt.structures.registry import (
    StructureDefinitionError,
    StructureRegistry,
    register_structure,
    StructureOverwriteError,
)
import pytest


async def test_structure_registration():
    registry = StructureRegistry(allow_overwrites=False)

    @register_structure(identifier="test", registry=registry)
    class SerializableObject:
        def __init__(self, number) -> None:
            super().__init__()
            self.number = number

        async def ashrink(self):
            return self.number

        @classmethod
        async def aexpand(cls, shrinked_value):
            return cls(shrinked_value)

    assert "test" in registry._identifier_shrinker_map, "Registration fails"
    assert "test" in registry._identifier_expander_map, "Registration of expand failed"
    assert (
        SerializableObject.aexpand == registry._identifier_expander_map["test"]
    ), "Is not the same instance"

    with pytest.raises(StructureOverwriteError):

        @register_structure(identifier="test", registry=registry)
        class SerializableObject:
            def __init__(self, number) -> None:
                super().__init__()
                self.number = number

            async def ashrink(self):
                return self.number

            @classmethod
            async def aexpand(cls, shrinked_value):
                return cls(shrinked_value)

    with pytest.raises(StructureDefinitionError):

        @register_structure(identifier="karl", registry=registry)
        class SerializableObject:
            def __init__(self, number) -> None:
                super().__init__()
                self.number = number

            @classmethod
            async def aexpand(cls, shrinked_value):
                return cls(shrinked_value)
