from ..log import LogDataModel, LogLevel
from ....messages.types import ASSIGN_LOG
from ....messages.base import MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = ASSIGN_LOG
    extensions: Optional[MetaExtensionsModel]


class AssignLogMessage(MessageModel):
    data: LogDataModel
    meta: MetaModel

    @classmethod
    def from_log(cls, reference,  message, loglevel = LogLevel.INFO, extensions={}):
        return cls(data={
            "level": loglevel,
            "message": message
            }, meta={"extensions": extensions, "reference": reference})