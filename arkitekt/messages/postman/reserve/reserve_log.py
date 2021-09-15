from ..log import LogDataModel
from ....messages.types import  RESERVE_LOG
from ....messages.base import MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = RESERVE_LOG
    extensions: Optional[MetaExtensionsModel]


class ReserveLogMessage(MessageModel):
    data: LogDataModel
    meta: MetaModel