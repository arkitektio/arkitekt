from pydantic import BaseModel
from arkitekt.actors.base import Actor
from arkitekt.api.schema import LogLevelInput
from arkitekt.messages import Assignation, Provision


class AssignationHelper(BaseModel):
    actor: Actor
    assignation: Assignation
    provision: Provision

    async def alog(self, level: LogLevelInput, message: str) -> None:
        raise NotImplementedError()


class ProvisionHelper(BaseModel):
    actor: Actor
    provision: Provision

    async def alog(self, level: LogLevelInput, message: str) -> None:
        raise NotImplementedError()


class ThreadedAssignationHelper(AssignationHelper):
    pass


class AsyncAssignationHelper(AssignationHelper):
    async def alog(self, message: str, level: LogLevelInput = LogLevelInput.DEBUG):
        await self.actor.transport.log_to_assignation(
            id=self.assignation.assignation, level=level, message=message
        )


class AsyncProvisionHelper(AssignationHelper):
    async def alog(self, message: str, level: LogLevelInput = LogLevelInput.DEBUG):
        await self.actor.transport.log_to_assignation(
            id=self.assignation.assignation, level=level, message=message
        )
