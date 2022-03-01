from typing import Any, Dict, List, Optional
from arkitekt.postmans.transport.base import PostmanTransport
from arkitekt.messages import Assignation, Reservation, Unassignation, Unreservation
from arkitekt.api.schema import AssignationStatus, ReservationStatus, ReserveParamsInput
from koil import unkoil, Koil
from arkitekt.postmans.vars import current_postman


class BasePostman:
    """Postman


    Postmans are the the messengers of the arkitekt platform, they are taking care
    of the communication between your app and the arkitekt-server.

    needs to implement:
        broadcast: On assignation Update or on reservation update (non updated fields are none)


    """

    def __init__(self, transport: PostmanTransport) -> None:
        self.transport = transport
        self.transport.abroadcast = self.abroadcast
        self._koil = None

    async def aconnect(self):
        await self.transport.aconnect()

    async def abroadcast(self):
        raise NotImplementedError(
            "This needs to be overwritten by your Postman subclass"
        )

    async def adisconnect(self):
        await self.transport.adisconnect()

    async def __aenter__(self):
        print("Connecting to the server")
        current_postman.set(self)
        await self.aconnect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.adisconnect()
        current_postman.set(None)
        return self

    def __enter__(self):
        self._koil.__enter__()
        return unkoil(self.__aenter__)

    def __exit__(self, exc_type, exc_val, exc_tb):
        unkoil(self.__aexit__, exc_type, exc_val, exc_tb)
        self._koil.__exit__(exc_type, exc_val, exc_tb)
        print("Unsetting Postman")
