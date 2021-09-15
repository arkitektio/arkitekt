from pydantic.main import BaseModel
from ....messages.types import  RESERVE_WAITING
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = RESERVE_WAITING
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    topic: Optional[str] #TODO: Maybe not optional
    message: Optional[str]

class ReserveWaitingMessage(MessageModel):
    data: DataModel
    meta: MetaModel