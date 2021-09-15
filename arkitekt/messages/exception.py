from ..messages.base import MessageDataModel, MessageMetaModel, MessageMetaExtensionsModel, MessageModel

from typing import Optional
from ..messages.types import EXCEPTION

class ProtocolException(Exception):
    pass

class ExceptionMetaModel(MessageMetaModel):
    type: str = EXCEPTION
    reference: str

class ExceptionDataModel(MessageDataModel):
    message: Optional[str]
    type: str = "Exception"


class ExceptionMessage(MessageModel):
    data: ExceptionDataModel
    meta: ExceptionMetaModel = {"type": EXCEPTION}


    @classmethod
    def fromException(cls, e: Exception, reference):
        return cls(data={"message": str(e), "type": e.__class__.__name__}, meta={"reference": reference})


    def toException(self):
        return ProtocolException(f'{self.data.type}: {self.data.message}')