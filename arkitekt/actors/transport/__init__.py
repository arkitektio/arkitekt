from typing import Awaitable, Callable, List, Protocol,Optional
from pydantic import BaseModel

from arkitekt.api.schema import AssignationStatus, LogLevelInput
from arkitekt.messages import Assignation


class ActorTransport(BaseModel):
    
    log_to_assignation: Callable[[str, LogLevelInput, str], Awaitable[None]]
    change_assignation: Callable[[Assignation, AssignationStatus, str], Awaitable[None]]
    list_assignations: Callable[[Optional[AssignationStatus]], List[Assignation]]



class SharedTransport(ActorTransport):
    log_to_assignation: Callable[[str, LogLevelInput, str], Awaitable[None]]
    change_assignation: Callable[[Assignation, AssignationStatus, str], Awaitable[None]]
    list_assignations: Callable[[Optional[AssignationStatus]], List[Assignation]]
