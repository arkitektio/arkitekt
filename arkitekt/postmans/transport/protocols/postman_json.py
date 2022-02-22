from typing import Any, Dict, List, Literal, Optional
import uuid

from pydantic import BaseModel, Field
from datetime import datetime
from arkitekt.messages import Assignation, Reservation, Unassignation, Unreservation
from arkitekt.api.schema import ReservationStatus, AssignationStatus, ReserveParamsInput
from enum import Enum


class PostmanMessageTypes(str, Enum):

    LIST_RESERVATION = "RESERVE_LIST"
    LIST_RESERVATION_REPLY = "RESERVE_LIST_REPLY"
    LIST_RESERVATION_DENIED = "RESERVE_LIST_DENIED"

    RESERVE = "RESERVE"
    RESERVE_REPLY = "RESERVE_REPLY"
    RESERVE_DENIED = "RESERVE_DENIED"

    UNRESERVE = "UNRESERVE"
    UNRESERVE_REPLY = "UNRESERVE_REPLY"
    UNRESERVE_DENIED = "UNRESERVE_DENIED"

    LIST_ASSIGNATION = "ASSIGN_LIST"
    LIST_ASSIGNATION_REPLY = "ASSIGN_LIST_REPLY"
    LIST_ASSIGNATION_DENIED = "ASSIGN_LIST_DENIED"

    ASSIGN = "ASSIGN"
    ASSIGN_REPLY = "ASSIGN_REPLY"
    ASSIGN_DENIED = "ASSIGN_DENIED"

    UNASSIGN = "UNASSIGN"
    UNASSIGN_REPLY = "UNASSIGN_REPLY"
    UNASSIGN_DENIED = "UNASSIGN_DENIED"


class PostmanSubMessageTypes(str, Enum):

    ASSIGN_UPDATE = "ASSIGN_UPDATE"
    RESERVE_UPDATE = "RESERVE_UPDATE"


class JSONMeta(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class JSONMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    meta: JSONMeta = Field(default_factory=JSONMeta)
    pass


class ReserveList(JSONMessage):
    type: Literal[
        PostmanMessageTypes.LIST_RESERVATION
    ] = PostmanMessageTypes.LIST_RESERVATION
    exclude: Optional[List[ReservationStatus]]


class ReserveListReply(JSONMessage):
    type: Literal[
        PostmanMessageTypes.LIST_RESERVATION_REPLY
    ] = PostmanMessageTypes.LIST_RESERVATION_REPLY
    reservations: List[Reservation]


class ReserveListDenied(JSONMessage):
    type: Literal[
        PostmanMessageTypes.LIST_RESERVATION_DENIED
    ] = PostmanMessageTypes.LIST_RESERVATION_DENIED
    error: str


class ReservePub(JSONMessage):
    type: Literal[PostmanMessageTypes.RESERVE] = PostmanMessageTypes.RESERVE
    params: Optional[ReserveParamsInput]
    node: Optional[str]
    template: Optional[str]
    title: Optional[str]


class ReservePubReply(JSONMessage, Reservation):
    type: Literal[PostmanMessageTypes.RESERVE_REPLY] = PostmanMessageTypes.RESERVE_REPLY


class ReservePubDenied(JSONMessage):
    type: Literal[
        PostmanMessageTypes.RESERVE_DENIED
    ] = PostmanMessageTypes.RESERVE_DENIED
    error: str


class UnreservePub(JSONMessage):
    type: Literal[PostmanMessageTypes.UNRESERVE] = PostmanMessageTypes.UNRESERVE
    reservation: str


class UnreservePubReply(JSONMessage, Unreservation):
    type: Literal[
        PostmanMessageTypes.UNRESERVE_REPLY
    ] = PostmanMessageTypes.UNRESERVE_REPLY


class UnreservePubDenied(JSONMessage):
    type: Literal[
        PostmanMessageTypes.UNRESERVE_DENIED
    ] = PostmanMessageTypes.UNRESERVE_DENIED
    error: str


class ReserveSubUpdate(JSONMessage, Reservation):
    type: Literal[
        PostmanSubMessageTypes.RESERVE_UPDATE
    ] = PostmanSubMessageTypes.RESERVE_UPDATE


class AssignList(JSONMessage):
    type: Literal[
        PostmanMessageTypes.LIST_ASSIGNATION
    ] = PostmanMessageTypes.LIST_ASSIGNATION
    exclude: Optional[List[AssignationStatus]]


class AssingListReply(JSONMessage):
    type: Literal[
        PostmanMessageTypes.LIST_ASSIGNATION_REPLY
    ] = PostmanMessageTypes.LIST_ASSIGNATION_REPLY
    assignations: List[Assignation]


class AssignListDenied(JSONMessage):
    type: Literal[
        PostmanMessageTypes.LIST_ASSIGNATION_DENIED
    ] = PostmanMessageTypes.LIST_ASSIGNATION_DENIED
    error: str


class AssignPub(JSONMessage):
    type: Literal[PostmanMessageTypes.ASSIGN] = PostmanMessageTypes.ASSIGN
    reservation: str
    args: List[Any]
    kwargs: Dict[str, Any]
    persist: bool = True
    log: bool = True


class AssignPubReply(JSONMessage, Assignation):
    type: Literal[PostmanMessageTypes.ASSIGN_REPLY] = PostmanMessageTypes.ASSIGN_REPLY
    assignation: str
    status: AssignationStatus


class AssignPubDenied(JSONMessage):
    type: Literal[PostmanMessageTypes.ASSIGN_DENIED] = PostmanMessageTypes.ASSIGN_DENIED
    error: str


class UnassignPub(JSONMessage):
    type: Literal[PostmanMessageTypes.UNASSIGN] = PostmanMessageTypes.UNASSIGN
    assignation: str


class UnassignPubReply(JSONMessage, Unassignation):
    type: Literal[
        PostmanMessageTypes.UNASSIGN_REPLY
    ] = PostmanMessageTypes.UNASSIGN_REPLY


class UnassignPubDenied(JSONMessage):
    type: Literal[
        PostmanMessageTypes.UNASSIGN_DENIED
    ] = PostmanMessageTypes.UNASSIGN_DENIED
    error: str


class AssignSubUpdate(JSONMessage, Assignation):
    type: Literal[
        PostmanSubMessageTypes.ASSIGN_UPDATE
    ] = PostmanSubMessageTypes.ASSIGN_UPDATE
