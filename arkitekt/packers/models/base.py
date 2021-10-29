from arkitekt.packers.structure import Structure, StructureDefaults
from pydantic import BaseModel

from arkitekt.schema.widgets import Widget


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
    def get_identifier(cls):
        return cls.get_meta().identifier

    @classmethod
    def get_defaults(cls) -> StructureDefaults:
        meta = cls.get_meta()
        return StructureDefaults(widget=getattr(meta, "default_widget", None))
