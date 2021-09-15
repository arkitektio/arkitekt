
from ..log import LogDataModel
from ....messages.types import UNASSIGN_LOG
from ....messages.base import MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = UNASSIGN_LOG
    extensions: Optional[MetaExtensionsModel]


class UnassignLogMessage(MessageModel):
    data: LogDataModel
    meta: MetaModel