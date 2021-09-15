from pydantic.main import BaseModel
from ....messages.types import  ASSIGN_RETURN, ASSIGN_YIELD, PROVIDE, PROVIDE_DONE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = ASSIGN_YIELD
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    returns: Optional[List] #TODO: Maybe not optional

class AssignYieldsMessage(MessageModel):
    data: DataModel
    meta: MetaModel