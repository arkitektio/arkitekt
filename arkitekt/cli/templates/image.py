""" An example of an image app for Arkitekt: it makes a random image, and blurs one"""

from typing import Optional

import numpy as np
import xarray as xr

from arkitekt import App, run
from mikro import Mikro, mikro_service
from mikro.api.schema import ArrayDataset

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


# The actions are what others call. An image travels between them by id: an action
# is handed the dataset, and the `mikro` client it asks for, and returns a new one.


@app.action
def generate_random_image(
    mikro: Mikro, width: int = 256, height: int = 256, name: str = "Random image"
) -> ArrayDataset:
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
    ArrayDataset
        The random image
    """
    pixels = xr.DataArray(random_pixels(width, height), dims=("y", "x"))
    return mikro.create_array_dataset(data=pixels, scales=[], name=name, axes=["y", "x"])


@app.action
def blur_image(image: ArrayDataset, mikro: Mikro, radius: int = 2) -> ArrayDataset:
    """Blur Image

    Blurs an image over the pixels around each one

    Parameters
    ----------
    image : ArrayDataset
        The image to blur, of two dimensions
    radius : int, optional
        How many pixels around each one are averaged, by default 2

    Returns
    -------
    ArrayDataset
        The blurred image, as large as the input
    """
    pixels = image.data.squeeze().compute().values
    if pixels.ndim != 2:
        raise ValueError(f"Only an image of two dimensions can be blurred, and this one has {pixels.ndim}")
    blurred = xr.DataArray(blur_pixels(pixels, radius), dims=("y", "x"))
    return mikro.create_array_dataset(data=blurred, scales=[], name=f"Blurred {image.name}", axes=["y", "x"])


if __name__ == "__main__":
    run(app)
