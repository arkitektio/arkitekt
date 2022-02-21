from typing import Dict
from .base import Transport
from .agent.base import AgentTransport
from .postman.base import PostmanTransport
from arkitekt.config import TransportProtocol
import logging

logger = logging.getLogger(__name__)


class TransportRegistry:
    def __init__(self) -> None:
        self.registeredAgentTransports: Dict[str, AgentTransport] = {}
        self.registeredPostmanTransports: Dict[str, PostmanTransport] = {}

    def register_agent_transport(
        self, protocol: TransportProtocol, transport: AgentTransport
    ):
        self.registeredAgentTransports[protocol] = transport

    def register_postman_transport(
        self, protocol: TransportProtocol, transport: PostmanTransport
    ):
        self.registeredPostmanTransports[protocol] = transport

    def get_postman_transport_for_protocol(self, protocol):
        return self.registeredPostmanTransports[protocol]

    def get_agent_transport_for_protocol(self, protocol):
        return self.registeredAgentTransports[protocol]


def register_agent_transport(protocol: TransportProtocol):
    def real_decorator(transport):

        assert issubclass(transport, Transport), "Transport must subclass Transport"
        logger.info(f"Registerying Agent Transport {transport} for {protocol}")
        get_current_transport_registry().register_agent_transport(protocol, transport)
        return transport

    return real_decorator


def register_postman_transport(protocol: TransportProtocol):
    def real_decorator(transport):

        assert issubclass(transport, Transport), "Transport must subclass Transport"
        logger.info(f"Registerying Postman Transport {transport} for {protocol}")
        get_current_transport_registry().register_postman_transport(protocol, transport)
        return transport

    return real_decorator


TRANSPORT_REGISTRY = None


def get_current_transport_registry(with_defaults=True):
    global TRANSPORT_REGISTRY
    if not TRANSPORT_REGISTRY:
        TRANSPORT_REGISTRY = TransportRegistry()
        if with_defaults:
            import arkitekt.transport.agent.websocket
            import arkitekt.transport.postman.websocket

    return TRANSPORT_REGISTRY
