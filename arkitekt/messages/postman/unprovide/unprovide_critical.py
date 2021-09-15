from ..exception import ExceptionDataModel
from pydantic.main import BaseModel
from ....messages.types import  PROVIDE, PROVIDE_CRITICAL, PROVIDE_DONE, UNPROVIDE_CRITICAL
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = UNPROVIDE_CRITICAL
    extensions: Optional[MetaExtensionsModel]

class UnprovideExceptionModel(ExceptionDataModel):
    provision: str


class UnprovideCriticalMessage(MessageModel):
    data: UnprovideExceptionModel
    meta: MetaModel