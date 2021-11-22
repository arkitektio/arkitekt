from arkitekt.packers.structure import Structure, StructureMeta
from pydantic import BaseModel
import inspect
from arkitekt.schema.widgets import Widget


def props(obj):
    pr = {}
    for name in dir(obj):
        value = getattr(obj, name)
        if not name.startswith("__") and not inspect.ismethod(value):
            pr[name] = value
    return pr


class StructureModel(Structure):
    """Model

    Model is the abstract baseclass of all Serverside Models and provides a Django ORM
    like interface for retrieving data from the Server.

    Implements:
        id (str): Every Model has an id (UUID) that identifies the Server Instance

    Args:
        BaseModel ([type]): [description]
        Structure ([type]): [description]
        metaclass ([type], optional): [description]. Defaults to ModelMeta.

    Raises:
        NotImplementedError: [description]
        NotImplementedError: [description]

    Returns:
        [type]: [description]
    """

    @classmethod
    def get_structure_meta(cls) -> StructureMeta:
        meta = props(cls.get_meta())
        return StructureMeta(**meta)
