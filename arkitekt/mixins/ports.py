from abc import abstractmethod
import asyncio


class Port:
    """
    Abstract class for serialization of data.

    """

    @abstractmethod
    async def cause_expand(self, value, registry):
        raise NotImplementedError()

    @abstractmethod
    async def cause_shrink(self, value, registry):
        raise NotImplementedError()


class ExpansionError:
    pass


class StructureExpander(Port):
    identifier: str

    async def cause_expand(self, value, registry):
        return await registry.get_expanded_for_identifier(self.identifier)(value)

    async def cause_shrink(self, value, registry):
        return registry.get_shrinker_for_identifier(self.identifier)(value)


class ListExpander(Port):
    child: Port

    async def cause_expand(self, value, registry):
        if self.child is None:
            raise ExpansionError("You need to specify a child")

        if isinstance(value, list):
            return await asyncio.gather(
                *[self.child.expand(item, registry) for item in value]
            )
        else:
            raise ExpansionError(f"Expected a list got {type(value)}")

    async def cause_shrink(self, value, registry):
        return await asyncio.gather(
            *[self.child.shrink(item, registry) for item in value]
        )


class IntExpander(Port):
    async def cause_expand(self, value, registry):
        if not isinstance(value, int):
            raise ExpansionError(f"Expected an int got {type(value)}")
        return value

    async def cause_shrink(self, value, registry):
        return int(value)


class StringExpander(Port):
    async def cause_expand(self, value, registry):
        if not isinstance(value, str):
            raise ExpansionError(f"Expected an str got {type(value)}")
        return value

    async def cause_shrink(self, value, registry):
        return str(value)


class DictExpander(Port):
    async def cause_expand(self, value, registry):
        if not isinstance(value, dict):
            raise ExpansionError(f"Expected an dict got {type(value)}")

        return value

    async def cause_shrink(self, value, registry):
        return str(value)


class EnumExpander(Port):
    async def cause_expand(self, value, registry):
        return value

    async def cause_shrink(self, value, registry):
        return str(value)


class BoolExpander(Port):
    async def cause_expand(self, value, registry):
        return bool(value)

    async def cause_shrink(self, value, registry):
        return bool(value)
