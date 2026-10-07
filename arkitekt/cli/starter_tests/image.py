"""The app for itself, with no server.

What the actions compute is tested as the plain functions it is, and
`local_runtime` starts the app as a run starts it. Run these with
`uv run pytest`; the release workflow does too.

Its actions store images, so calling them needs the service: those tests are in
`test___ENTRYPOINT___hub.py`.
"""

import numpy as np
import pytest
from arkitekt.runtime import Runtime

from __ENTRYPOINT__ import app, blur_pixels, random_pixels


def test_random_pixels_have_the_size_asked_for():
    pixels = random_pixels(width=8, height=4)

    assert pixels.shape == (4, 8)
    assert 0 <= pixels.min() and pixels.max() < 1


def test_the_same_seed_is_the_same_image():
    assert np.array_equal(random_pixels(8, 4, seed=1), random_pixels(8, 4, seed=1))
    assert not np.array_equal(random_pixels(8, 4, seed=1), random_pixels(8, 4, seed=2))


def test_an_image_without_pixels_is_refused():
    with pytest.raises(ValueError, match="at least one pixel"):
        random_pixels(width=0, height=4)


def test_a_blur_keeps_the_size_and_evens_the_image_out():
    pixels = random_pixels(32, 32, seed=1)

    blurred = blur_pixels(pixels, radius=2)

    assert blurred.shape == pixels.shape
    assert blurred.var() < pixels.var()


def test_a_blur_leaves_a_flat_image_as_it_is():
    assert np.allclose(blur_pixels(np.ones((6, 6)), radius=2), 1.0)


def test_a_blur_of_no_radius_changes_nothing():
    pixels = random_pixels(8, 8, seed=1)

    assert np.array_equal(blur_pixels(pixels, radius=0), pixels)


def test_the_app_starts_and_offers_both_actions(local_runtime: Runtime[None]):
    assert local_runtime.app is app
    assert {"generate_random_image", "blur_image"} <= set(app.registry.implementations)
