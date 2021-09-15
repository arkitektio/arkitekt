from pydantic.main import BaseModel
from ....messages.types import  PROVIDE, PROVIDE_DONE, RESERVE_DONE, UNRESERVE_DONE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = UNRESERVE_DONE
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    reservation: str #TODO: Maybe not optional

class UnreserveDoneMessage(MessageModel):
    data: DataModel
    meta: MetaModel