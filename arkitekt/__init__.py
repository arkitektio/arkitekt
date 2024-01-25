def missing_install(name: str, error: Exception):
    def real_missing_install(*args, **kwargs):
        raise ImportError(
            "Missing import: rekuest_next. Please install the missing package. "
        ) from error

    return real_missing_install


try:
    from rekuest.register import register, register_structure, PortGroupInput as group
    from rekuest.agents.hooks import background, startup
    from rekuest.actors.reactive.api import (
        log,
        alog,
        progress,
        aprogress,
        useGuardian,
        useInstanceID,
        useUser,
    )

except ImportError as e:
    register = missing_install("rekuest", e)
    register_structure = missing_install("rekuest", e)
    group = missing_install("rekuest", e)
    log = missing_install("rekuest", e)
    alog = missing_install("rekuest", e)
    progress = missing_install("rekuest", e)
    aprogress = missing_install("rekuest", e)
    useGuardian = missing_install("rekuest", e)
    useInstanceID = missing_install("rekuest", e)
    useUser = missing_install("rekuest", e)
    background = missing_install("rekuest", e)
    startup = missing_install("rekuest", e)


try:
    from rekuest_next.register import register as register_next
except ImportError:
    register_next = missing_install("rekuest_next", e)

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
    "background",
    "startup",
    "register_next",
]
