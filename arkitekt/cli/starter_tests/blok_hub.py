"""The agent against the services it uses: its actions, storing real images.

`teststack` logs the app in to a hub made for the tests. It needs Docker and
konstruktor, and about a minute to start, so these are not part of a bare
`uv run pytest`: every test here is marked `hub`. Run them with
`uv run pytest -m hub`.

What needs no server is tested in `test___ENTRYPOINT__.py`.
"""

import pytest
from arkitekt.testing import TestStack
from mikro import Mikro

# Every test in this file runs against a hub.
pytestmark = pytest.mark.hub


def test_a_test_image_is_stored(teststack: TestStack[None]):
    image = teststack.call("generate_test_image", objects=4, size=64)

    stored = teststack.runtime.require(Mikro).get_array_dataset(image.id)
    assert stored.name == "Test image of 4 blobs"
    assert stored.data.squeeze().shape == (64, 64)


def test_analysing_a_stored_image_updates_the_state(teststack: TestStack[None]):
    image = teststack.call("generate_test_image", objects=4, size=64)

    found = teststack.call("analyse_image", image=image)

    state = teststack.runtime.agent.states["Analysis"]
    assert found >= 1 and state.objects == found
    assert state.image_name == "Test image of 4 blobs"
    assert state.history[0] == f"Test image of 4 blobs: {found} objects"
    assert (state.busy, state.status) == (False, "Idle")


def test_the_objects_of_an_image_are_stored_as_an_image_of_their_own(teststack: TestStack[None]):
    image = teststack.call("generate_test_image", objects=4, size=64)

    objects = teststack.call("segment_image", image=image)

    assert objects.name == "Objects of Test image of 4 blobs"
    labels = objects.data.squeeze().compute().values
    assert labels.shape == (64, 64)
    assert labels.max() == teststack.runtime.agent.states["Analysis"].objects
