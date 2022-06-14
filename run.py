

from arkitekt.actors.functional import FunctionalGenActor
from arkitekt.agents.transport.mock import MockAgentTransport
from arkitekt.api.schema import ProvisionFragment, ProvisionStatus
from arkitekt.structures.registry import StructureRegistry

async def assign(*args, **kwargs):
    yield args, kwargs

print(FunctionalGenActor(transport=MockAgentTransport(), provision=ProvisionFragment(id=1, status=ProvisionStatus.PENDING), structure_registry=StructureRegistry(), assign=assign))