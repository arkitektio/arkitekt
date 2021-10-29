from ..log import LogDataModel
from enum import Enum
from pydantic.main import BaseModel
from ....messages.types import PROVIDE_TRANSITION
from ....messages.base import (
    MessageDataModel,
    MessageMetaExtensionsModel,
    MessageMetaModel,
    MessageModel,
)
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


class ProvideMode(str, Enum):
    # Start State
    DEBUG = "DEBUG"
    PRODUCTION = "PRODUCTION"


class ProvideTransistionData(MessageDataModel):
    state: ProvideState
    mode: ProvideMode = ProvideMode.PRODUCTION
    message: Optional[str]


class ProvideTransitionMessage(MessageModel):
    data: ProvideTransistionData
    meta: MetaModel

    @classmethod
    def from_critical(cls, reference, exception, extensions={}):
        return cls(
            data={"message": str(exception), "state": ProvideState.CRITICAL},
            meta={"extensions": extensions, "reference": reference},
        )
