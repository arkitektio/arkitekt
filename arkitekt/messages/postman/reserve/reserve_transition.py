
from ..log import LogDataModel
from enum import Enum
from pydantic.main import BaseModel
from ....messages.types import  RESERVE_TRANSITION
from ....messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import List, Optional


class MetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class MetaModel(MessageMetaModel):
    type: str = RESERVE_TRANSITION
    extensions: Optional[MetaExtensionsModel]


class ReserveState(str, Enum):
    # Start State
    #Start State
    STARTING = "STARTING"
    ROUTING = "ROUTING"
    # Life States
    PROVIDING = "PROVIDING"
    WAITING = "WAITING"
    DISCONNECT = "DISCONNECT"


    REROUTING = "REROUTING"
    CANCELING = "CANCELING"
    ACTIVE = "ACTIVE"

    # End States
    ERROR = "ERROR"
    ENDED = "ENDED"
    CANCELLED = "CANCELLED"
    CRITICAL = "CRITICAL"


class ReserveTransitionData(MessageDataModel):
    state: ReserveState
    message: Optional[str]


class ReserveTransitionMessage(MessageModel):
    data: ReserveTransitionData
    meta: MetaModel