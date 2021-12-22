from arkitekt.transport.base import Transport, TransportConfig


class PostmanTransportConfig(TransportConfig):
    pass


class PostmanTransport(Transport):
    configClass = PostmanTransportConfig
    config: PostmanTransportConfig
