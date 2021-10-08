from abc import abstractmethod
from typing import Callable, Coroutine, Type
from arkitekt.messages.base import MessageModel
from enum import Enum
import asyncio
from herre import Herre
from herre.herre import get_current_herre
from koil import Koil
from koil.koil import get_current_koil
from konfik.config.base import Config
from konfik.konfik import Konfik, get_current_konfik
import pydantic


class TransportConfig(Config):
    pass

class TansportConfigError(Exception):
    pass

class Transport(object):
    configClass = TransportConfig

    def __init__(self, config_dict, broadcast = None, herre: Herre = None, koil: Koil = None, konfik: Konfik = None, **kwargs) -> None:
        self._broadcast = broadcast
        assert self._broadcast is not None, "Please provide a broadcaster that receives messages"
        self.herre = herre or get_current_herre()
        self.koil = koil or get_current_koil()
        self.loop = self.koil.loop

        try:
            self.config = self.configClass(**config_dict)
        except pydantic.error_wrappers.ValidationError as e:
            raise TansportConfigError(f"Found a non valid Configuration {config_dict}") from e


    @abstractmethod
    def aconnect(self):
        raise NotImplementedError()


    @abstractmethod
    def adisconnect(self):
        raise NotImplementedError()

    async def broadcast(self, message: MessageModel):
        return await self._broadcast(message)


    @abstractmethod
    async def forward(self, message: MessageModel):
        raise NotImplementedError()



