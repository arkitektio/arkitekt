from .params import ReserveParams
from pydantic.main import BaseModel
from ....messages.types import  RESERVE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional



class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    with_progress: Optional[bool] = False

class MetaModel(MessageMetaModel):
    type: str = RESERVE
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    node: Optional[str] #TODO: Maybe not optional
    template: Optional[str]
    provision: Optional[str]
    params: Optional[ReserveParams]


class ReserveMessage(MessageModel):
    data: DataModel
    meta: MetaModel