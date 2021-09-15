from .params import ProvideParams
from ....messages.generics import Context
from pydantic.main import BaseModel
from ....messages.types import  BOUNCED_PROVIDE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional



class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = BOUNCED_PROVIDE
    extensions: Optional[MetaExtensionsModel]
    context: Context

class DataModel(MessageDataModel):
    node: Optional[str] #TODO: Maybe not optional
    template: Optional[str]
    params: Optional[ProvideParams]


class BouncedProvideMessage(MessageModel):
    data: DataModel
    meta: MetaModel