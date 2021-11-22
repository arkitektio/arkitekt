from typing import Callable, Coroutine, Type, TypeVar
import inspect

import pydantic

from arkitekt.packers.structure import StructureMeta

class PackerError(Exception):
    pass

class MetaNotValidError(Exception):
    pass

class UnpackableError(PackerError):
    pass

class NoStructureRegisteredError(PackerError):
    pass

class StructureOverwriteError(PackerError):
    pass


class PackerRegistry:

    def __init__(self) -> None:
        self.identifierStructureMap = {}

    def register_structure(self, structure):

        try:
            assert inspect.ismethod(structure.get_structure_meta) and structure.get_structure_meta.__self__ is structure, f"{structure}.get_structure_meta  must be either provided for be a classmethod"
            assert inspect.ismethod(structure.expand) and structure.expand.__self__ is structure,"Expand Function must be an async classmethod"
            assert inspect.iscoroutinefunction(structure.expand), "Expand Function must be an (classmethod) async function"
            assert inspect.iscoroutinefunction(structure.shrink), "Shrink Function must be an async function"

        except Exception as e:
            raise UnpackableError(str(e)) from e

        try:
            meta: StructureMeta = structure.get_structure_meta()
        except pydantic.error_wrappers.ValidationError as e:
            raise MetaNotValidError(f"{structure} does not return a Valid Meta object") from e

        if meta.identifier in self.identifierStructureMap and not meta.overwrite:
            raise StructureOverwriteError(f"Another Structure was registerd for identifier '{meta.identifier}'. You can choose to overwrite setting the Meta attribute to overwrite=True")
        self.identifierStructureMap[meta.identifier] = structure


    def get_structure(self, identifier):
        try:
            return self.identifierStructureMap[identifier]
        except KeyError as e:
            raise NoStructureRegisteredError(f"No Structure registered for identifier {identifier}") from e

PACKER_REGISTRY = None

def get_packer_registry():
    global PACKER_REGISTRY
    if not PACKER_REGISTRY:
        PACKER_REGISTRY = PackerRegistry()
    return PACKER_REGISTRY



def register_structure(
    meta: StructureMeta = None,
    overwrite: bool = False,
    registry: PackerRegistry=  None,
):
    """Registers a Structure

    Registers a Structure with the a Package Registry. Once registered Arkitekt will use this Structure to expand and shrink Node requests.

    Args:
        identifier (str, optional): A unique identifier to be known be. Defaults to None.
        overwrite (bool, optional): If overwrite is set this Structure will replace exisiting Structures, otherwise we return an error on Reigstration
        registry (PackerRegistry, optional): Which registry to use in order to register this Strucute. Will use the default Registry if not set
    """

    def real_decorator(cls):
        if meta: cls.get_structure_meta = classmethod(lambda cls: meta)
        (registry or get_packer_registry()).register_structure(cls)
        return cls


    return real_decorator















