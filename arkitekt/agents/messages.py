from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel

from arkitekt.agents.base import ClientID, UserID


class Meta(BaseModel):
    name: str
    description: str
    version: str


class Error(BaseModel):
    type: str
    message: str


class Context(BaseModel):
    app: ClientID
    user: UserID  # TODO: Make this optional?


class AssignMessage(BaseModel):
    type: Literal["assign"]
    correlation_id: str
    reservation: str  # TODO: Is that interesting?, probably not
    provision: str
    args: Optional[List[Any]]
    kwargs: Optional[Dict[Any]]
    context: Context


class AssignLog(BaseModel):
    type: Literal["assign_progress"]
    correlation_id: str
    state: str


class AssignReturnMessage(BaseModel):
    type: Literal["assign_return"]
    correlation_id: str
    provision: str
    returns: Optional[List[Any]]


class AssignYieldMessage(BaseModel):
    type: Literal["assign_yield"]
    correlation_id: str
    provision: str
    returns: Optional[List[Any]]


class AssignDoneMessage(BaseModel):
    type: Literal["assign_done"]
    correlation_id: str
    provision: str
    returns: Optional[List[Any]]


class AssignCriticalMessage(BaseModel):
    type: Literal["assign_critical"]
    correlation_id: str
    provision: str
    error: Error
