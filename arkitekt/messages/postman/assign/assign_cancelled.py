from pydantic.main import BaseModel
from ....messages.types import ASSIGN_CANCELLED
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = ASSIGN_CANCELLED
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    canceller: Optional[str] # A reference to the cancelling agent

    
class AssignCancelledMessage(MessageModel):
    data: DataModel
    meta: MetaModel