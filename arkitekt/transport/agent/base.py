from arkitekt.transport.base import Transport, TransportConfig
import logging

logger = logging.getLogger(__name__)


class AgentTransportConfig(TransportConfig):
    identifier: str = "main"

    @property
    def protocol(self):
        return "wss" if self.secure else "ws"


class AgentTransport(Transport):
    configClass = AgentTransportConfig
