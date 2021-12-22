from abc import abstractmethod
from typing import Callable, Coroutine, Type
from arkitekt.messages.base import MessageModel
from enum import Enum
import asyncio
from herre import Herre
from herre.herre import get_current_herre
from koil import Koil
from koil.koil import get_current_koil
from fakts import Fakts, get_current_fakts, Config
import pydantic


class TransportConfig(Config):
    pass


class TansportConfigError(Exception):
    pass


class Transport(object):
    configClass = TransportConfig

    def __init__(
        self,
        config_dict,
        broadcast=None,
        herre: Herre = None,
        koil: Koil = None,
        fakts: Fakts = None,
        **kwargs,
    ) -> None:
        self._broadcast = broadcast
        assert (
            self._broadcast is not None
        ), "Please provide a broadcaster that receives messages"
        self.herre = herre or get_current_herre()
        self.fakts = fakts or get_current_fakts()

        try:
            self.config = self.configClass(**config_dict)
        except pydantic.error_wrappers.ValidationError as e:
            raise TansportConfigError(f"Non valid Configuration {config_dict}") from e

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
