# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "arkitekt[mikro]>=3",
#   "scikit-image>=0.24",
#   "pooch>=1.8",
#   "xarray>=2024.3.0",
#   "numpy>=1.26",
# ]
# ///
"""Calling: a script that uploads an image and then exits.

Run:  uv run --script examples/upload_cells3d.py

`easy` is the other direction from `run`: you name the *services* you need and
it hands you their clients. Nothing connects until the `with` block is entered.

The image is scikit-image's `cells3d` — a two-channel (membrane, nuclei) z-stack
of cells, 60 planes of 256x256, fetched through pooch on first use (~80 MB).

Afterwards the dataset is in mikro, with a three-level pyramid so the frontend
can show it without loading the whole volume.
"""

import numpy as np
import xarray as xr
from skimage import data

from arkitekt import easy
from mikro import dataset_arrays, mikro_service
from mikro.api.schema import CoordinateAnchorInput


def main() -> None:
    """Fetch the sample stack and put it into mikro."""
    # cells3d comes back as (z, c, y, x); mikro wants its axes ordered
    # time -> channel -> space, so the channel axis moves in front.
    raw = data.cells3d()
    volume = xr.DataArray(
        np.moveaxis(raw, 1, 0).astype("uint16"), dims=("c", "z", "y", "x")
    )

    with easy("cells3d-upload", mikro_service) as mikro:
        folder = mikro.create_folder(name="examples")

        # `data` *is* level 0 and `scales` only what is coarser than it —
        # passing the base in both would upload it twice.
        level_zero, scales = dataset_arrays(volume, levels=3, method="mean")

        dataset = mikro.create_array_dataset(
            data=level_zero,
            scales=scales,
            name="cells3d",
            axes=["c", "z", "y", "x"],
            folder=folder.id,
            # One histogram per channel: membrane and nuclei get their own
            # contrast limits rather than a shared, wrong one.
            anchors=CoordinateAnchorInput.histogram_anchors(volume),
        )

        # A scene is what the frontend renders. Its kind is inferred from what
        # was recorded (a z axis makes this a volume), so nothing restates it.
        dataset.intrinsic_system.stage(name="Default")
        print(f"uploaded {dataset.id}: {dataset.data.shape}")


if __name__ == "__main__":
    main()
