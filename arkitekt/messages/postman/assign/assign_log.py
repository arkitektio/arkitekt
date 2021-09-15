from ..log import LogDataModel
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