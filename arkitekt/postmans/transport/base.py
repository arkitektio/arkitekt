from typing import Awaitable, Callable, List, Optional, Dict, Any, Union

from arkitekt.messages import Assignation, Reservation, Unassignation, Unreservation
from arkitekt.api.schema import AssignationStatus, ReservationStatus, ReserveParamsInput
from koil.composition import KoiledModel


class PostmanTransport(KoiledModel):
    instance_id: Optional[str]

    _abroadcast: Optional[Callable[[Union[Assignation, Reservation]], Awaitable[None]]]

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

    class Config:
        underscore_attrs_are_private = True
