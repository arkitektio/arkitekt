from typing import Any, Dict, List, Optional, TypeVar
from pydantic import BaseModel
from arkitekt.api.schema import (
    ProvisionStatus,
    ReservationStatus,
    AssignationStatus,
)

T = TypeVar("T", bound=BaseModel)


class UpdatableModel(BaseModel):
    pass

    def update(self: T, other: BaseModel, in_place=True) -> Optional[T]:
        if in_place:
            for key, value in other.dict().items():
                if key in self.__fields__:
                    if value != None:  # None is not a valid update!
                        setattr(self, key, value)
        else:
            copy = self.copy()
            copy.update(other)
            return copy


class Assignation(UpdatableModel):
    assignation: str
    provision: Optional[str]
    reservation: Optional[str]
    args: Optional[List[Any]]
    kwargs: Optional[Dict[str, Any]]
    returns: Optional[List[Any]]
    persist: Optional[bool]
    log: Optional[bool]
    status: Optional[AssignationStatus]


class Unassignation(UpdatableModel):
    assignation: str
    provision: Optional[str]


class Provision(UpdatableModel):
    provision: str
    template: Optional[str]
    status: Optional[ProvisionStatus]


class Unprovision(UpdatableModel):
    provision: str


class Reservation(UpdatableModel):
    reservation: str
    template: Optional[str]
    node: Optional[str]
    status: Optional[ReservationStatus] = None


class Unreservation(BaseModel):
    reservation: str
