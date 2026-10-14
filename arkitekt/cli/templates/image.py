""" An example of an image app for Arkitekt: it makes a random image, and blurs one"""

from typing import Optional

import numpy as np
import xarray as xr

from arkitekt import App, run
from mikro import Mikro, mikro_service
from mikro.api.schema import IdentityTransformInput, LensDerivedFromInput
from mikro.arkitekt.specs import Image

# The version of the app. A release is the commit tagged with it (v1.2.3).
__version__ = __APP_VERSION__

# The app is a declaration: who it is, what it offers, and the services it uses.
# `arkitekt run` finds it in this module (as `app`) and runs it; so does
# `python app.py`, below.
app = App(__APP_ARGUMENTS__, services=[mikro_service])


# What the actions compute is plain numpy, apart from them: it needs no server,
# so it is tested without one (see tests/).


def random_pixels(width: int, height: int, seed: Optional[int] = None) -> np.ndarray:
    """A (height, width) image of random values between 0 and 1."""
    if width < 1 or height < 1:
        raise ValueError("An image needs to be at least one pixel wide and high")
    return np.random.default_rng(seed).random((height, width))


def blur_pixels(pixels: np.ndarray, radius: int = 2) -> np.ndarray:
    """Replace every pixel of a (y, x) image by the mean of the ``radius`` pixels around it."""
    if radius < 0:
        raise ValueError("The radius cannot be negative")
    size = 2 * radius + 1
    padded = np.pad(pixels, radius, mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, (size, size))
    return windows.mean(axis=(-2, -1))


# The actions are what others call. An image travels between them as a lens: a
# selection over a stored array, the whole of it or a crop, handed over by id. `Image`
# is a lens of two space axes, so an input typed on it is offered only images, and a
# result typed on it is checked to be one. An action is handed the lens, and the
# `mikro` client it asks for, and stores what it makes as a new array whose whole lens
# it returns.


@app.action
def generate_random_image(
    mikro: Mikro, width: int = 256, height: int = 256, name: str = "Random image"
) -> Image:
    """Generate Random Image

    Makes an image of random pixels

    Parameters
    ----------
    width : int, optional
        How many pixels wide the image is, by default 256
    height : int, optional
        How many pixels high the image is, by default 256
    name : str, optional
        What the image is called, by default "Random image"

    Returns
    -------
    Image
        The random image
    """
    pixels = xr.DataArray(random_pixels(width, height), dims=("y", "x"))
    stored = mikro.create_array_dataset(data=pixels, scales=[], name=name, axes=["y", "x"])
    return stored.lens()


@app.action
def blur_image(image: Image, mikro: Mikro, radius: int = 2) -> Image:
    """Blur Image

    Blurs an image over the pixels around each one

    Parameters
    ----------
    image : Image
        The image to blur: a lens of two dimensions, the whole image or a crop of it
    radius : int, optional
        How many pixels around each one are averaged, by default 2

    Returns
    -------
    Image
        The blurred image, as large as the input
    """
    pixels = image.data.squeeze().compute().values
    if pixels.ndim != 2:
        raise ValueError(f"Only an image of two dimensions can be blurred, and this one has {pixels.ndim}")
    blurred = mikro.create_array_dataset(
        data=xr.DataArray(blur_pixels(pixels, radius), dims=("y", "x")),
        scales=[],
        name=f"Blurred {image.label}",
        axes=["y", "x"],
        # Computed from the lens, pixel for pixel: it is placed wherever the lens is.
        derived_from=[LensDerivedFromInput(lens=image.id, transform=IdentityTransformInput())],
    )
    return blurred.lens()


if __name__ == "__main__":
    run(app)
