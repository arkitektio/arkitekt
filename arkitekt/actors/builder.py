from arkitekt.actors.base import Actor
from arkitekt.agents.transport.base import AgentTransport
from arkitekt.messages import Provision


class ActorBuilder:
    def build_actor(self, provision: Provision, transport: AgentTransport) -> Actor:
        raise NotImplementedError(
            "If you decide to use the mixin you need to implement this method"
        )
