from typing import Callable
from arkitekt.actors.base import Actor
from arkitekt.agents.transport.base import AgentTransport

from arkitekt.messages import Provision


ActorBuilder = Callable[[Provision, AgentTransport], Actor]
