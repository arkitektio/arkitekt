from typing import Any, Dict, List
from pydantic import BaseModel


class Assignation(BaseModel):
    assignation: str
    provision: str
    reservation: str
    args: List[Any]
    kwargs: Dict[str, Any]
    persist: bool = True
    log: bool = True


class Unassignation(BaseModel):
    assignation: str


class Provision(BaseModel):
    provision: str
    template: str


class Unprovision(BaseModel):
    provision: str
