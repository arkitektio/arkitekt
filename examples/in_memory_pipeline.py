# /// script
# requires-python = ">=3.11"
# dependencies = ["arkitekt>=3", "tifffile>=2024.5.22", "scikit-image>=0.24", "numpy>=1.26"]
# ///
"""Offering: three actions that hand a numpy array to each other, on the agent.

Run:  uv run --script examples/in_memory_pipeline.py

A port may only name a class the app knows. ``app.memory_structure(np.ndarray)``
declares one whose instances *stay here*: the array is kept by this agent and
what travels is a reference to it, so `read_tiff -> segment -> count` can be
wired into a workflow without a data layer in between.

Use this for scratch data inside one pipeline. Anything worth keeping belongs in
mikro — see `upload_cells3d.py` and `denoise_volume.py`.
"""

from pathlib import Path
from typing import Annotated

import numpy as np
import tifffile
from skimage import measure
from skimage.filters import gaussian, threshold_otsu

from arkitekt import App, Description, run

app = App("in-memory-pipeline", "0.1.0")

# Neither numpy nor this app owns a data layer: the instances live on the agent
# and travel as a reference to it.
app.memory_structure(np.ndarray, description="A numpy array held by this agent")

DEMO_TIFF = Path.home() / ".arkitekt-examples" / "demo_cells.tif"


@app.action
def write_demo_tiff() -> str:
    """Write Demo Tiff

    Writes a small synthetic two-cell field to disk and returns its path, so the
    other actions have something to read without a download.
    """
    DEMO_TIFF.parent.mkdir(parents=True, exist_ok=True)
    y, x = np.mgrid[0:256, 0:256]
    blobs = np.zeros((256, 256), dtype=np.float32)
    for cy, cx, r in ((70, 70, 18), (180, 80, 22), (120, 190, 15)):
        blobs += np.exp(-(((y - cy) ** 2 + (x - cx) ** 2) / (2 * r**2)))
    noisy = blobs + np.random.default_rng(42).normal(0, 0.05, blobs.shape)
    tifffile.imwrite(DEMO_TIFF, noisy.astype(np.float32))
    return str(DEMO_TIFF)


@app.action
def read_tiff(path: Annotated[str, Description("A TIFF on this machine")]) -> np.ndarray:
    """Read Tiff

    Reads a TIFF with tifffile. The array stays on this agent.
    """
    return np.asarray(tifffile.imread(path))


@app.action
def segment(
    image: np.ndarray,
    sigma: Annotated[float, Description("Smoothing before thresholding")] = 2.0,
) -> np.ndarray:
    """Segment

    Otsu-thresholds a smoothed copy and labels the connected components.
    """
    smoothed = gaussian(image.astype(np.float32), sigma=sigma)
    return measure.label(smoothed > threshold_otsu(smoothed))


@app.action
def count_objects(labels: np.ndarray) -> int:
    """Count Objects

    How many labels the mask carries, background excluded.
    """
    return int(labels.max())


if __name__ == "__main__":
    run(app)
