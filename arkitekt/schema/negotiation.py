from enum import Enum, auto
from typing import Optional
from arkitekt.config import TransportProtocol
from herre.access.object import GraphQLObject



class AgentSettings(GraphQLObject):
    type: TransportProtocol
    kwargs: dict

class PostmanSettings(GraphQLObject):
    type: TransportProtocol
    kwargs: dict

class Transcript(GraphQLObject):
    postman: Optional[PostmanSettings]
    agent: Optional[AgentSettings]
