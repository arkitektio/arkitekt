from arkitekt.actors.base import Actor, Agent
from arkitekt.messages import Provision


class ActorBuilder:
    def build_actor(self, provision: Provision, agent: Agent) -> Actor:
        raise NotImplementedError(
            "If you decide to use the mixin you need to implement this method"
        )
