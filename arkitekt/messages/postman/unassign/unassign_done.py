from pydantic.main import BaseModel
from pydantic.types import OptionalInt
from ....messages.types import  ASSIGN_RETURN, PROVIDE, PROVIDE_DONE, UNASSIGN_DONE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = UNASSIGN_DONE
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    assignation: str

class UnassignDoneMessage(MessageModel):
    data: DataModel
    meta: MetaModel