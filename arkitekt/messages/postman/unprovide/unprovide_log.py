from ..log import LogDataModel
from ....messages.types import UNPROVIDE_LOG
from ....messages.base import MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = UNPROVIDE_LOG
    extensions: Optional[MetaExtensionsModel]

class UnprovideLogData(LogDataModel):
    provision: str


class UnprovideLogMessage(MessageModel):
    data: UnprovideLogData
    meta: MetaModel