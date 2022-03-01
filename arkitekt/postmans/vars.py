import contextvars
from typing import Any

current_postman = contextvars.ContextVar("current_postman", default=None)


def get_current_postman() -> Any:
    return current_postman.get()
