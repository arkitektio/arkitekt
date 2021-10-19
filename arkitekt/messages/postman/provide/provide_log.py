from ..log import LogDataModel, LogLevel
from enum import Enum
from pydantic.main import BaseModel
from ....messages.types import  PROVIDE_LOG
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = PROVIDE_LOG
    extensions: Optional[MetaExtensionsModel]


class ProvideLogMessage(MessageModel):
    data: LogDataModel
    meta: MetaModel

    @classmethod
    def from_log(cls, reference,  message, loglevel = LogLevel.INFO, extensions={}):
        return cls(data={
            "level": loglevel,
            "message": message
            }, meta={"extensions": extensions, "reference": reference})