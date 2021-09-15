from ...messages.types import ASSIGN
from ...messages.base import MessageDataModel, MessageMetaExtensionsModel, MessageMetaModel, MessageModel
from typing import Optional


class AssignMetaExtensionsModel(MessageMetaExtensionsModel):
    # Set by postman consumer
    progress: Optional[str]
    callback: Optional[str]

class AssignMetaModel(MessageMetaModel):
    type: str = ASSIGN
    extensions: Optional[AssignMetaExtensionsModel]

class AssignDataModel(MessageDataModel):

    node: Optional[int] #TODO: Maybe not optional
    pod: Optional[int]
    template: Optional[int]

    inputs: dict
    params: Optional[dict]


class AssignMessage(MessageModel):
    data: AssignDataModel
    meta: AssignMetaModel