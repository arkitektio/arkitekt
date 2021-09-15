
from ..base import MessageDataModel



class ExceptionDataModel(MessageDataModel):
    type: str
    message: str