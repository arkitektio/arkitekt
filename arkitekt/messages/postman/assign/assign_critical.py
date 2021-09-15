from ..exception import ExceptionDataModel
from pydantic.main import BaseModel
from ....messages.types import  ASSIGN_CRITICAL
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = ASSIGN_CRITICAL
    extensions: Optional[MetaExtensionsModel]

class AssignCriticalMessage(MessageModel):
    data: ExceptionDataModel
    meta: MetaModel