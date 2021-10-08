from typing import Dict
from .base import Transport
from arkitekt.config import TransportProtocol


class TransportRegistry:

    def __init__(self) -> None:
        self.registeredTransports: Dict[str, Transport] = {}

    def register_transport(self, protocol: TransportProtocol,  transport: Transport):
        self.registeredTransports[protocol] = transport

    def get_transport_for_protocol(self,protocol):
        return self.registeredTransports[protocol]

    
def register_transport(protocol: TransportProtocol):
    print("Registering Transport")

    def rea_decorator(grant):
        assert issubclass(grant, Transport), "Transport must subclass Transport"
        get_current_transport_registry().register_transport(protocol, grant)
        return grant

    return rea_decorator



GRANT_REGISTRY = None


def get_current_transport_registry(with_defaults=True):
    global GRANT_REGISTRY
    if not GRANT_REGISTRY:
        GRANT_REGISTRY = TransportRegistry()
        if with_defaults:
            import arkitekt.transport.websocket 


    return GRANT_REGISTRY