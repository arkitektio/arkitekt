from ....messages.generics import Context
from pydantic.main import BaseModel
from ....messages.types import  BOUNCED_ASSIGN, BOUNCED_UNASSIGN, BOUNCED_FORWARDED_UNASSIGN
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional



class AssignParams(BaseModel):
    providers: Optional[List[str]]

class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = BOUNCED_UNASSIGN
    extensions: Optional[MetaExtensionsModel]
    context: Context

class DataModel(MessageDataModel):
    assignation: str
    provision: str

class BouncedForwardedUnassignMessage(MessageModel):
    data: DataModel
    meta: MetaModel