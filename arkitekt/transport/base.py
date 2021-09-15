from abc import abstractmethod
from typing import Callable, Coroutine, Type
from arkitekt.messages.base import MessageModel
from herre.config.base import BaseConfig
from herre.auth import get_current_herre
from enum import Enum
import asyncio

class TransportConfig(BaseConfig):
    _group = "arkitekt.postman"
    pass

class Transport(object):


    def __init__(self, broadcast = None) -> None:
        self._broadcast = broadcast

        assert self._broadcast is not None, "Please provide a broadcaster that receives messages"

        self.herre = get_current_herre()
        self.loop = get_current_herre().loop


    @abstractmethod
    def connect(self):
        raise NotImplementedError()


    @abstractmethod
    def disconnect(self):
        raise NotImplementedError()

    async def broadcast(self, message: MessageModel):
        return await self._broadcast(message)


    @abstractmethod
    async def forward(self, message: MessageModel):
        raise NotImplementedError()



