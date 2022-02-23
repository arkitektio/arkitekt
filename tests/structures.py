from pydantic.main import BaseModel


class SerializableObject(BaseModel):
    number: int

    async def shrink(self):
        return self.number

    @classmethod
    async def expand(cls, shrinked_value):
        return cls(number=shrinked_value)


class SecondSerializableObject:
    async def shrink(self):
        return 5

    @classmethod
    async def expand(cls, shrinked_value):
        return cls()


class SecondObject:
    pass

    def __init__(self, id) -> None:
        self.id = id
