def missing_rekuest_install(*args, **kwargs):
    raise ImportError("Missing import: rekuest. Please install the missing package. ")


def missing_rekuest_next_install(*args, **kwargs):
    raise ImportError(
        "Missing import: rekuest_next. Please install the missing package. "
    )


try:
    from rekuest.register import register, register_structure, PortGroupInput as group
    from rekuest.actors.reactive.api import (
        log,
        alog,
        progress,
        aprogress,
        useGuardian,
        useInstanceID,
        useUser,
    )

except ImportError:
    register = missing_rekuest_install
    register_structure = missing_rekuest_install
    group = missing_rekuest_install
    log = missing_rekuest_install
    alog = missing_rekuest_install
    progress = missing_rekuest_install
    aprogress = missing_rekuest_install
    useGuardian = missing_rekuest_install
    useInstanceID = missing_rekuest_install
    useUser = missing_rekuest_install


try:
    from rekuest_next.register import register as register_next
except ImportError:
    register_next = missing_rekuest_next_install

from .builders import easy, publicqt, jupy, scheduler, next
from .apps.types import App

__all__ = [
    "App",
    "register",
    "easy",
    "publicqt",
    "jupy",
    "log",
    "alog",
    "progress",
    "aprogress",
    "scheduler",
    "register_structure",
    "group",
    "useGuardian",
    "useInstanceID",
    "useUser",
    "next",
]
