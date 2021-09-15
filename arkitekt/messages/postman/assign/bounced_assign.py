from ....messages.generics import Context
from pydantic.main import BaseModel
from ....messages.types import  BOUNCED_ASSIGN
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional



class AssignParams(BaseModel):
    providers: Optional[List[str]]

class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = BOUNCED_ASSIGN
    extensions: Optional[MetaExtensionsModel]
    context: Context

class DataModel(MessageDataModel):
    reservation: str # The reservation reference we are going to assign to
    args: Optional[list]
    kwargs: Optional[dict]

class BouncedAssignMessage(MessageModel):
    data: DataModel
    meta: MetaModel