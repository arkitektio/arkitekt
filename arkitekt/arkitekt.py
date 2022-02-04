import os
from arkitekt.errors import NoArkitektFound
from rath import rath
import contextvars
import logging

current_arkitekt = contextvars.ContextVar("current_arkitekt", default=None)
GLOBAL_ARKITEKT = None


logger = logging.getLogger(__name__)


def set_current_arkitekt(herre, set_global=True):
    global GLOBAL_ARKITEKT
    current_arkitekt.set(herre)
    if set_global:
        GLOBAL_ARKITEKT = herre


def set_global_arkitekt(herre):
    global GLOBAL_ARKITEKT
    GLOBAL_ARKITEKT = herre


def get_current_arkitekt(allow_global=True):
    global GLOBAL_ARKITEKT
    arkitekt = current_arkitekt.get()

    if not arkitekt:
        if not allow_global:
            raise NoArkitektFound(
                "No current mikro found and global mikro are not allowed"
            )
        if not GLOBAL_ARKITEKT:
            if os.getenv("ARKITEKT_ALLOW_ARKITEKT_GLOBAL", "True") == "True":
                try:

                    from arkitekt.fakts.arkitekt import FaktsArkitekt

                    GLOBAL_ARKITEKT = FaktsArkitekt()
                    return GLOBAL_ARKITEKT
                except ImportError as e:
                    raise NoArkitektFound("Error creating Fakts Mikro") from e
            else:
                raise NoArkitektFound(
                    "No current mikro found and and no global mikro found"
                )

        return GLOBAL_ARKITEKT

    return arkitekt


class Arkitekt(rath.Rath):
    pass
