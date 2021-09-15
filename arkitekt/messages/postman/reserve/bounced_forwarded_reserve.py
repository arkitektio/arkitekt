from ....messages.generics import Context
from pydantic.main import BaseModel
from .params import ReserveParams
from ....messages.types import  BOUNCED_FORWARDED_RESERVE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional

class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = BOUNCED_FORWARDED_RESERVE
    extensions: Optional[MetaExtensionsModel]
    context: Context

class DataModel(MessageDataModel):
    node: Optional[str] #TODO: Maybe not optional
    template: Optional[str]
    params: Optional[ReserveParams]
    provision: str

class BouncedForwardedReserveMessage(MessageModel):
    data: DataModel
    meta: MetaModel