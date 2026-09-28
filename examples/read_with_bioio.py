# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "arkitekt[mikro]>=3",
#   "bioio>=3.5",
#   "bioio-ome-tiff>=1.4",
#   "tifffile>=2024.5.22",
#   "xarray>=2024.3.0",
#   "numpy>=1.26",
# ]
# ///
"""Calling: whatever bioio can read, into mikro.

Run:  uv run --script examples/read_with_bioio.py [image.ome.tiff]

bioio is the reader front-end: one API over many formats, each format a plugin.
Only `bioio-ome-tiff` is installed here on purpose — `bioio-bioformats` would
pull a JRE on first import, which is not what a first example should do.

With no argument a small OME-TIFF is written with tifffile first.

bioio always reports five dimensions, `TCZYX`, padding the ones the file does
not have. Size-1 padding is dropped here rather than uploaded: an axis mikro
does not need is an axis that has to be explained later.
"""

import sys
import tempfile
from pathlib import Path

import numpy as np
import tifffile
import xarray as xr
from bioio import BioImage

from arkitekt import easy
from mikro import mikro_service
from mikro.api.schema import CoordinateAnchorInput


def synthesise(path: Path) -> Path:
    """Write a small two-channel z-stack as an OME-TIFF."""
    rng = np.random.default_rng(3)
    stack = rng.poisson(40, (2, 12, 128, 128)).astype("uint16")
    tifffile.imwrite(path, stack, metadata={"axes": "CZYX"}, ome=True)
    return path


def main(path: Path) -> None:
    """Read with bioio and upload the dimensions the file actually has."""
    image = BioImage(path)
    array = image.get_image_data(image.dims.order)  # "TCZYX"

    # Drop the padded singletons, keep the names for the ones that survive.
    kept = [
        (name.lower(), size)
        for name, size in zip(image.dims.order, array.shape, strict=True)
        if size > 1
    ]
    squeezed = xr.DataArray(
        array.reshape([size for _, size in kept]), dims=[name for name, _ in kept]
    )
    print(f"{path.name}: {image.dims.order} {array.shape} -> {squeezed.dims}")

    with easy("bioio-upload", mikro_service) as mikro:
        dataset = mikro.create_array_dataset(
            data=squeezed,
            scales=[],
            name=path.name,
            # Bare names are enough: mikro knows t is time, c channel, zyx space.
            axes=list(squeezed.dims),
            anchors=CoordinateAnchorInput.histogram_anchors(squeezed),
        )
        dataset.stage(name="Default")
        print(f"uploaded {dataset.id}: {dataset.data.shape}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(Path(sys.argv[1]))
    else:
        with tempfile.TemporaryDirectory() as tmp:
            main(synthesise(Path(tmp) / "synthetic.ome.tiff"))
