"""The app's actions, called for real: through their ports, with no server.

`call` starts the app as a run starts it and calls an action by name (or by the
function itself). Run these with `uv run pytest`; the release workflow does too.
"""

from collections.abc import Callable
from typing import Any


def test_append_world(call: Callable[..., Any]) -> None:
    assert call("append_world", hello="Hello") == "Hello World"


def test_generate_n_string_yields_the_last_string_last(
    call: Callable[..., Any],
) -> None:
    assert call("generate_n_string", n=2, timeout=0) == "Hello 1"
