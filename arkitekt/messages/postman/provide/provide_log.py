from ..log import LogDataModel
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