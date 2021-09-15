from pydantic.main import BaseModel
from ....messages.types import  RESERVE_ACTIVE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = RESERVE_ACTIVE
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    topic: Optional[str] #TODO: Maybe not optional

class ReserveActiveMessage(MessageModel):
    data: DataModel
    meta: MetaModel