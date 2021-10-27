from typing import Dict
from .base import Transport
from arkitekt.config import TransportProtocol
import logging

logger = logging.getLogger(__name__)

class TransportRegistry:

    def __init__(self) -> None:
        self.registeredTransports: Dict[str, Transport] = {}

    def register_transport(self, protocol: TransportProtocol,  transport: Transport):
        self.registeredTransports[protocol] = transport

    def get_transport_for_protocol(self,protocol):
        return self.registeredTransports[protocol]

    
def register_transport(protocol: TransportProtocol):

    def real_decorator(transport):

        assert issubclass(transport, Transport), "Transport must subclass Transport"
        logger.info(f"Registerying Transport {transport} for {protocol}")
        get_current_transport_registry().register_transport(protocol, transport)
        return transport

    return real_decorator



GRANT_REGISTRY = None


def get_current_transport_registry(with_defaults=True):
    global GRANT_REGISTRY
    if not GRANT_REGISTRY:
        GRANT_REGISTRY = TransportRegistry()
        if with_defaults:
            import arkitekt.transport.websocket 


    return GRANT_REGISTRY