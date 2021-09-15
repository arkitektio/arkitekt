
from ..log import LogDataModel
from enum import Enum
from pydantic.main import BaseModel
from ....messages.types import  PROVIDE_TRANSITION
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = PROVIDE_TRANSITION
    extensions: Optional[MetaExtensionsModel]


class ProvideState(str, Enum):
    # Start State
    PENDING = "PENDING"
    PROVIDING = "PROVIDING"
    
    # Life States
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    CANCELING = "CANCELING"
    DISCONNECTED = "LOST"
    RECONNECTING = "RECONNECTING"
    # End States
    DENIED = "DENIED"

    # End States
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    ENDED = "ENDED"
    CANCELLED = "CANCELLED"


class ProvideTransistionData(MessageDataModel):
    state: ProvideState
    message: Optional[str]


class ProvideTransitionMessage(MessageModel):
    data: ProvideTransistionData
    meta: MetaModel