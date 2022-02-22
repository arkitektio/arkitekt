from enum import Enum
from typing import Optional
from fakts import Config


class TransportProtocol(Enum):
    WEBSOCKET = "WEBSOCKET"
    KAFKA = "KAFKA"
    RABBITMQ = "RABBITMQ"


class PostmanSettings(Config):
    type: TransportProtocol = TransportProtocol.WEBSOCKET
    kwargs: dict = {}


class AgentSettings(Config):
    type: TransportProtocol = TransportProtocol.WEBSOCKET
    debug: bool = False
    kwargs: dict = {}


class ArkitektConfig(Config):
    host: str
    port: int
    secure: bool
    postman: Optional[PostmanSettings]
    agent: Optional[AgentSettings]

    class Config:
        group = "arkitekt"
        env_prefix = "arkitekt_"

    @property
    def endpoint(self):
        return f"http://{self.host}:{self.port}/graphql"
