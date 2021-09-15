from pydantic.main import BaseModel
from ....messages.types import  RESERVE, UNRESERVE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional



class ProvideMetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class ProvideMetaModel(MessageMetaModel):
    type: str = UNRESERVE
    extensions: Optional[ProvideMetaExtensionsModel]

class DataModel(MessageDataModel):
    reservation: str



class UnreserveMessage(MessageModel):
    data: DataModel
    meta: ProvideMetaModel