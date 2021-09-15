from pydantic.main import BaseModel
from ....messages.types import  ASSIGN_RETURN, PROVIDE, PROVIDE_DONE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = ASSIGN_RETURN
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    returns: Optional[List] #TODO: Maybe not optional

class AssignReturnMessage(MessageModel):
    data: DataModel
    meta: MetaModel