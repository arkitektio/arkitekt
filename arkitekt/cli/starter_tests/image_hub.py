"""The app against the services it uses: its actions, storing real images.

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


def test_a_random_image_is_stored(teststack: TestStack[None]):
    image = teststack.call("generate_random_image", width=16, height=8, name="noise")

    stored = teststack.runtime.require(Mikro).get_array_dataset(image.id)
    assert stored.name == "noise"
    assert stored.data.squeeze().shape == (8, 16)


def test_a_blurred_image_is_as_large_and_smoother(teststack: TestStack[None]):
    image = teststack.call("generate_random_image", width=16, height=16)

    blurred = teststack.call("blur_image", image=image, radius=2)

    assert blurred.name == "Blurred Random image"
    assert blurred.data.squeeze().shape == (16, 16)
    assert float(blurred.data.var()) < float(image.data.var())
