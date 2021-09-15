from ....messages.generics import Context
from ....messages.types import BOUNCED_UNRESERVE
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional

class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = BOUNCED_UNRESERVE
    extensions: Optional[MetaExtensionsModel]
    context: Context

class DataModel(MessageDataModel):
    reservation: str

class BouncedUnreserveMessage(MessageModel):
    data: DataModel
    meta: MetaModel