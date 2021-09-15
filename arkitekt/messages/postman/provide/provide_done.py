from pydantic.main import BaseModel
from ....messages.types import  PROVIDE, PROVIDE_DONE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = PROVIDE_DONE
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    pod: Optional[int] #TODO: Maybe not optional

class ProvideDoneMessage(MessageModel):
    data: DataModel
    meta: MetaModel