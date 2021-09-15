from pydantic.main import BaseModel
from ...messages.types import AGENT_DISCONNECT
from ...messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = AGENT_DISCONNECT
    extensions: Optional[MetaExtensionsModel]

class DataModel(MessageDataModel):
    canceller: Optional[str] # A reference to the cancelling agent

    
class AgentDisconnectMessage(MessageModel):
    data: DataModel
    meta: MetaModel