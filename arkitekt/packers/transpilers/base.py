from arkitekt.packers.structure import Structure
from typing import Callable
import inspect
import logging
import asyncio

logger = logging.getLogger(__name__)



class Transpiler():
    """A Transpiler registers for
    certain non native models and established
    a conversion algrohythm for an aritekt model
    """

    def __init__(self, type, structure, transpile: Callable, untranspile: Callable, loop=None, register=True) -> None:
        try:
            assert not issubclass(type, Structure), "Type cannot be a subclass of structure because structure are transpiled anyways"
            assert issubclass(structure, Structure), "structure must be a subclass of Structure in order to transpile to them"
        except Exception as e:
            raise Exception(f"Configuration Error: {type} , {structure}") from e
        self.type_name = type.__name__
        self.structure_name = structure.get_identifier()
        self.type = type
        self.structure = structure
        self.transpile_is_async = inspect.iscoroutinefunction(transpile)
        self._transpile = transpile

        self.untranspile_is_async = inspect.iscoroutinefunction(untranspile)
        self._untranspile = untranspile

        if register:

            from arkitekt.packers.transpilers.registry import get_transpiler_registry
            get_transpiler_registry().register_transpiler(self)
        

    async def transpile(self, object):
        logger.info(f"Transpiling from {self.type} to {self.structure}")
        if self.transpile_is_async: return await self._transpile(object)
        return await asyncio.get_event_loop().run_in_executor(None, self._transpile, object)

    async def untranspile(self, object):
        logger.info(f"Transpiling from {self.type} to {self.structure}")
        if self.untranspile_is_async: return await self._untranspile(object)
        return await asyncio.get_event_loop().run_in_executor(None, self._untranspile, object)



