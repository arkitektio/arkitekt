from pydantic.main import BaseModel


class SerializableObject(BaseModel):
    number: int

    async def ashrink(self):
        return self.number

    @classmethod
    async def aexpand(cls, shrinked_value):
        return cls(number=shrinked_value)


class SecondSerializableObject:
    async def ashrink(self):
        return 5

    @classmethod
    async def aexpand(cls, shrinked_value):
        return cls()


class IdentifiableSerializableObject(BaseModel):
    number: int

    @classmethod
    def get_identifier(cls):
        return "mock.identifiable"

    async def ashrink(self):
        return self.number

    @classmethod
    async def aexpand(cls, shrinked_value):
        return cls(number=shrinked_value)


class SecondObject:
    pass

    def __init__(self, id) -> None:
        self.id = id
