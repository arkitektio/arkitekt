# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "arkitekt[rekuest,mikro]>=5",
#   "scipy>=1.13",
#   "xarray>=2024.3.0",
#   "numpy>=1.26",
# ]
# ///
"""Offering: an action that takes an image from mikro and writes one back.

Run:  uv run --script examples/denoise_volume.py

`Volume` is not a new type: it is a lens over a mikro array dataset, annotated
with what the action needs to be true of it. Saying `Volume` in the signature is
what makes the UI offer only volumes here — the check is in the type, not in a
paragraph of prose.

The result is uploaded as its own dataset with a derivation edge back to the
input, so the server knows the two share a grid and the frontend can overlay
them.
"""

from typing import Annotated

import numpy as np
import xarray as xr
from scipy import ndimage

from arkitekt import App, Description, Task, run
from mikro import Mikro, mikro_service
from mikro.arkitekt.specs import Volume, ensure

app = App("denoise-volume", "0.1.0", services=[mikro_service])


@app.action
def denoise(
    mikro: Mikro,  # The mikro service is needed to create the result dataset (arkitekt injects it automatically)
    task: Task,  # The task is needed to report progress (arkitekt injects it automatically)
    volume: Annotated[Volume, Description("The stack to smooth")],  # The input volume to denoise
    sigma: Annotated[float, Description("Gaussian width, in pixels")] = 1.5,
) -> Volume:
    """Denoise Volume

    Smooths a stack with a gaussian and stores the result on the same grid.
    """
    # `.data` fetches the array behind the lens as a lazy s3 backed xarray DataArray
    source = volume.data
    task.progress(20, f"Smoothing {source.shape}")

    smoothed = xr.DataArray(
        ndimage.gaussian_filter(np.asarray(source), sigma=sigma), dims=source.dims
    )
    task.progress(70, "Uploading")

    result = mikro.create_array_dataset(
        data=smoothed,  # We just created this array, so we can pass it directly to mikro to store it.
        scales=[],
        name=f"denoised (sigma={sigma})",
        # We need to tell mikro what axes the result has, so it can be used in the same way as the input. The lens' `carried_axes` method copies the axes from the input volume to the output.
        axes=volume.carried_axes(smoothed.dims),
        # Same grid as this very input, with the values transformed.
        derived_from=[
            # We transformed the values, but we neither translared nor rotated the original image so a point in the input corresponds to the same point in the output, however we changed the values, so we use TRANSFORMED. If we had rotated or translated the image, we would need to use a different volume.derive_affine(...) call to describe the relationship between the two datasets.
            volume.derive_identity(value_relation="TRANSFORMED")
        ],
    )
    return ensure(result.lens(), Volume)


if __name__ == "__main__":
    run(app)
