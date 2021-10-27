from pydantic.main import BaseModel
from ....messages.types import  ASSIGN_RECEIVED
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = ASSIGN_RECEIVED
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    provision: str

class AssignReceivedMessage(MessageModel):
    data: DataModel
    meta: MetaModel