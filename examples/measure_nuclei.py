# /// script
# requires-python = ">=3.11"
# dependencies = ["arkitekt>=3", "scikit-image>=0.24", "numpy>=1.26", "pooch>=1.8"]
# ///
"""Offering: a real bioimage computation behind a plain signature.

Run:  uv run --script examples/measure_nuclei.py

The image never leaves the agent — segmentation happens locally on one of
scikit-image's own sample images, and only the numbers travel. The result is an
``@app.model``: a class whose fields become the ports of the return value, so
the caller gets a typed record rather than a blob.

The first run may download the sample image through ``pooch`` (~2 MB).
"""

from typing import Annotated

import numpy as np
from skimage import data, measure
from skimage.filters import threshold_otsu

from arkitekt import App, Description, Task, run

app = App("measure-nuclei", "0.1.0")


@app.model
class NucleiMeasurement:
    """What a segmented field of nuclei amounts to."""

    count: int
    mean_area_px: float
    median_area_px: float
    covered_fraction: float


@app.action
def measure_nuclei(
    min_size: Annotated[int, Description("Objects smaller than this are noise")] = 20,
    *,
    task: Task,
) -> NucleiMeasurement:
    """Measure Nuclei

    Segments scikit-image's `human_mitosis` field by Otsu thresholding and
    reports what the connected components add up to.
    """
    image = data.human_mitosis()
    task.progress(30, "Thresholding")

    mask = image > threshold_otsu(image)
    task.progress(60, "Labelling")

    labels = measure.label(mask)
    # Filter on the measured areas rather than on the mask: one pass, and no
    # dependence on which skimage version spells the size filter how.
    areas = np.array(
        [r.area for r in measure.regionprops(labels) if r.area >= min_size], dtype=float
    )
    task.progress(90, f"Found {areas.size} nuclei")

    return NucleiMeasurement(
        count=int(areas.size),
        mean_area_px=float(areas.mean()) if areas.size else 0.0,
        median_area_px=float(np.median(areas)) if areas.size else 0.0,
        covered_fraction=float(mask.mean()),
    )


if __name__ == "__main__":
    run(app)
