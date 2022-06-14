from pydantic import BaseModel
from arkitekt.actors.base import Actor
from arkitekt.api.schema import LogLevelInput
from arkitekt.messages import Assignation


class AssignationHelper(BaseModel):
    actor: Actor
    assignation: Assignation

    async def alog(self, level: LogLevelInput, message: str) -> None:
        raise NotImplementedError()

    class Config:
        arbitrary_types_allowed = True
        


class ProvisionHelper(BaseModel):
    actor: Actor

    async def alog(self, level: LogLevelInput, message: str) -> None:
        raise NotImplementedError()


class ThreadedAssignationHelper(AssignationHelper):
    pass


class AsyncAssignationHelper(AssignationHelper):
    async def alog(self, message: str, level: LogLevelInput = LogLevelInput.DEBUG):
        await self.actor.transport.log_to_assignation(
            id=self.assignation.assignation, level=level, message=message
        )


class AsyncProvisionHelper(ProvisionHelper):
    async def alog(self, message: str, level: LogLevelInput = LogLevelInput.DEBUG):
        await self.actor.transport.log_to_provision(
            id=self.actor.provision.id, level=level, message=message
        )
