"""The app's actions, called for real: through their ports, with no server.

`call` starts the app as a run starts it and calls an action by name (or by the
function itself). Run these with `uv run pytest`; the release workflow does too.
"""

import pytest
from arkitekt.testing import LocalCallError


def test_moving_average_smooths_over_the_window(call):
    assert call("moving_average", values=[0.0, 3.0, 6.0], window=2) == [0.0, 1.5, 4.5]


def test_moving_average_refuses_an_empty_window(call):
    with pytest.raises(LocalCallError, match="at least 1"):
        call("moving_average", values=[1.0], window=0)


def test_threshold_zeroes_what_is_below_the_cutoff(call):
    assert call("threshold", values=[0.2, 0.7], cutoff=0.5) == [0.0, 0.7]
