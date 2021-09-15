from ..exception import ExceptionDataModel
from pydantic.main import BaseModel
from ....messages.types import UNASSIGN_CRITICAL
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = UNASSIGN_CRITICAL
    extensions: Optional[MetaExtensionsModel]


class UnassignCriticalMessage(MessageModel):
    data: ExceptionDataModel
    meta: MetaModel