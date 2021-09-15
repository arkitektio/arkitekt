from pydantic.main import BaseModel
from ....messages.types import  ASSIGN, PROVIDE, UNASSIGN
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    with_progress: bool = False

class MetaModel(MessageMetaModel):
    '''The reference of the metamodel representats the assignation on the platform '''
    type: str = UNASSIGN
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    assignation: str


class UnassignMessage(MessageModel):
    data: DataModel
    meta: MetaModel