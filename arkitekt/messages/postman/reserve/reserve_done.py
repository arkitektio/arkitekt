from pydantic.main import BaseModel
from ....messages.types import  PROVIDE, PROVIDE_DONE, RESERVE_DONE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = RESERVE_DONE
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    topic: Optional[str] #TODO: Maybe not optional

class ReserveDoneMessage(MessageModel):
    data: DataModel
    meta: MetaModel