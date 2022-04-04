from typing import Any, Dict, List, Optional, TypeVar
from pydantic import BaseModel
from arkitekt.api.schema import (
    LogLevelInput,
    ProvisionStatus,
    ReservationStatus,
    AssignationStatus,
)

T = TypeVar("T", bound=BaseModel)


class UpdatableModel(BaseModel):
    pass

    def update(self: T, use: BaseModel = None, in_place=True, **kwargs) -> Optional[T]:
        if in_place:
            if use:
                for key, value in use.dict().items():
                    if key in self.__fields__:
                        if value != None:  # None is not a valid update!
                            setattr(self, key, value)
            if kwargs:
                for key in kwargs:
                    setattr(self, key, kwargs[key])

            return self
        else:
            copy = self.copy()
            copy.update(use=use, **kwargs)
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
    message: Optional[str]


class Unassignation(UpdatableModel):
    assignation: str
    provision: Optional[str]


class Provision(UpdatableModel):
    provision: str
    template: Optional[str]
    status: Optional[ProvisionStatus]


class Unprovision(UpdatableModel):
    provision: str
    message: Optional[str]


class Reservation(UpdatableModel):
    reservation: str
    template: Optional[str]
    node: Optional[str]
    status: Optional[ReservationStatus] = None
    message: Optional[str] = ""


class Unreservation(BaseModel):
    reservation: str


class AssignationLog(BaseModel):
    assignation: str
    level: LogLevelInput
    message: Optional[str]


class ProvisionLog(BaseModel):
    provision: str
    level: LogLevelInput
    message: Optional[str]
