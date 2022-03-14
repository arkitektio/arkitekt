from typing import Any, Dict, List, Optional
from arkitekt.postmans.transport.base import PostmanTransport
from arkitekt.messages import Assignation, Reservation, Unassignation, Unreservation
from arkitekt.api.schema import AssignationStatus, ReservationStatus, ReserveParamsInput
from koil import unkoil, Koil
from arkitekt.postmans.vars import current_postman
from koil.decorators import koilable


@koilable(add_connectors=True)
class BasePostman:
    """Postman


    Postmans are the the messengers of the arkitekt platform, they are taking care
    of the communication between your app and the arkitekt-server.

    needs to implement:
        broadcast: On assignation Update or on reservation update (non updated fields are none)


    """

    def __init__(self, transport: PostmanTransport) -> None:
        self.transport = transport

    async def abroadcast(self):
        raise NotImplementedError(
            "This needs to be overwritten by your Postman subclass"
        )

    async def __aenter__(self):
        self._token = current_postman.set(self)
        self.transport.abroadcast = self.abroadcast
        await self.transport.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.transport.__aexit__(exc_type, exc_val, exc_tb)
        current_postman.set(None)
