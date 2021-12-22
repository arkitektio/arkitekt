from ..exception import ExceptionDataModel
from pydantic.main import BaseModel
from ....messages.types import PROVIDE, PROVIDE_BOUND, PROVIDE_CRITICAL, PROVIDE_DONE
from ....messages.base import (
    MessageDataModel,
    MessageMetaExtensionsModel,
    MessageMetaModel,
    MessageModel,
)
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]


class MetaModel(MessageMetaModel):
    type: str = PROVIDE_BOUND
    extensions: Optional[MetaExtensionsModel]


class DataModel(MessageDataModel):
    agent: str


class ProvideBoundMessage(MessageModel):
    data: DataModel
    meta: MetaModel
