from ..log import LogDataModel
from ....messages.types import  UNRESERVE_LOG
from ....messages.base import  MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = UNRESERVE_LOG
    extensions: Optional[MetaExtensionsModel]


class UnreserveLogMessage(MessageModel):
    data: LogDataModel
    meta: MetaModel