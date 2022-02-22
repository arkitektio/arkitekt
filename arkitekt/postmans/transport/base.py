from typing import List, Optional, Dict, Any, Union
from arkitekt.messages import Assignation, Reservation, Unassignation, Unreservation
from arkitekt.api.schema import AssignationStatus, ReservationStatus, ReserveParamsInput


class PostmanTransport:
    pass

    async def aconnect():
        pass

    async def adisconnect():
        pass

    async def abroadcast(self, message: Union[Assignation, Reservation]):
        raise NotImplementedError("soinsoisn")

    async def aassign(
        self,
        reservation: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        persist=True,
        log=False,
    ) -> Assignation:
        raise NotImplementedError()

    async def aunassign(self, assignation: str) -> Unassignation:
        raise NotImplementedError()

    async def areserve(
        self,
        node: str,
        params: ReserveParamsInput = None,
    ) -> Reservation:
        raise NotImplementedError()

    async def aunreserve(
        self,
        reservation: str,
    ) -> Unreservation:
        raise NotImplementedError()

    async def alist_assignations(
        self, exclude: Optional[AssignationStatus] = None
    ) -> List[Assignation]:
        raise NotImplementedError()

    async def alist_reservations(
        self, exclude: Optional[ReservationStatus] = None
    ) -> List[Reservation]:
        raise NotImplementedError()
