from ....messages.exception import ExceptionMessage
from pydantic.main import BaseModel
from ....messages.types import  PROVIDE, PROVIDE_CRITICAL, PROVIDE_DONE, UNRESERVE_CRITICAL
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = UNRESERVE_CRITICAL
    extensions: Optional[MetaExtensionsModel]

class UnreserveCriticalMessage(ExceptionMessage):
    meta: MetaModel