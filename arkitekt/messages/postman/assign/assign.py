from pydantic.main import BaseModel
from ....messages.types import  ASSIGN, PROVIDE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    with_progress: bool = False

class MetaModel(MessageMetaModel):
    '''The reference of the metamodel representats the assignation on the platform '''
    type: str = ASSIGN
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    reservation: str # The reservation reference we are going to assign to
    args: Optional[list]
    kwargs: Optional[dict]

class AssignMessage(MessageModel):
    data: DataModel
    meta: MetaModel