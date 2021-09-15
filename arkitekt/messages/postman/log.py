

from enum import Enum
from ..base import MessageDataModel


class LogLevel(str, Enum):
    INFO = "INFO"
    DEBUG = "DEBUG"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    WARN = "WARN"


class LogDataModel(MessageDataModel):
    level: LogLevel
    message: str

    @classmethod
    def from_log(cls, message, level=LogLevel.INFO):
        return cls(level=level, message=message)