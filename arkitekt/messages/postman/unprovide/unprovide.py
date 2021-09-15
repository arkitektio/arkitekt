from pydantic.main import BaseModel
from ....messages.types import  PROVIDE, UNPROVIDE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional

class ProvideParams(BaseModel):
    providers: Optional[List[str]]


class ProvideMetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class ProvideMetaModel(MessageMetaModel):
    type: str = UNPROVIDE
    extensions: Optional[ProvideMetaExtensionsModel]

class DataModel(MessageDataModel):
    provision: str


class UnprovideMessage(MessageModel):
    data: DataModel
    meta: ProvideMetaModel