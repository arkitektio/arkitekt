# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "arkitekt[mikro]>=3",
#   "nibabel>=5.2",
#   "xarray>=2024.3.0",
#   "numpy>=1.26",
# ]
# ///
"""Calling: a NIfTI volume from disk into mikro.

Run:  uv run --script examples/upload_nifti.py [volume.nii.gz]

With no argument a small synthetic brain-shaped volume is written to a temp
directory first, so the example runs on any machine.

The one thing worth care: NIfTI indexes its data (i, j, k) with i fastest, while
mikro names axes outermost-first. So the array is reversed into (z, y, x) — the
same reversal every NIfTI ingest needs, and the usual way a volume gets silently
transposed.
"""

import sys
import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np
import xarray as xr

from arkitekt import easy
from mikro import mikro_service
from mikro.api.schema import CoordinateAnchorInput


def synthesise(path: Path) -> Path:
    """Write a small NIfTI so the example has something to read."""
    # Built in NIfTI's own (i, j, k) order, i fastest — 64 x 64 x 48.
    i, j, k = np.mgrid[0:64, 0:64, 0:48]
    ball = ((i - 32) ** 2 + (j - 32) ** 2 + (k - 24) ** 2) < 20**2
    data = (ball * 800 + np.random.default_rng(0).normal(0, 30, ball.shape)).astype(
        "float32"
    )
    nib.save(nib.Nifti1Image(data, affine=np.diag([1.0, 1.0, 2.0, 1.0])), path)
    return path


def main(path: Path) -> None:
    """Read the volume and upload it as a (z, y, x) dataset."""
    image = nib.load(path)
    # (i, j, k) -> (z, y, x): reversed, not transposed by name.
    array = np.asarray(image.dataobj).T
    print(f"{path.name}: {image.shape} (i,j,k) -> {array.shape} (z,y,x)")
    volume = xr.DataArray(array, dims=("z", "y", "x"))

    with easy("nifti-upload", mikro_service) as mikro:
        dataset = mikro.create_array_dataset(
            data=volume,
            scales=[],
            name=path.name,
            axes=["z", "y", "x"],
            anchors=[CoordinateAnchorInput.histogram_anchor(volume)],
        )
        dataset.stage(name="Default")
        print(f"uploaded {dataset.id}: {dataset.data.shape}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(Path(sys.argv[1]))
    else:
        with tempfile.TemporaryDirectory() as tmp:
            main(synthesise(Path(tmp) / "synthetic.nii.gz"))
