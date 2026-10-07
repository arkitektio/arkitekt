# /// script
# requires-python = ">=3.11"
# dependencies = ["arkitekt[rekuest,elektro]>=5", "scipy>=1.13", "xarray>=2024.3.0", "numpy>=1.26"]
# ///
"""Offering: spike detection over a trace that already lives in elektro.

Run:  uv run --script examples/detect_spikes.py

`SingleChannelTrace` is a lens over an elektro dataset, annotated with what this
action needs: a time axis, and at most one channel. A multichannel recording
still fits once the caller pins a channel — the constraint is on what arrives,
not on what is stored.

The result goes back as a trace of the same shape, one where every sample is
zero except the detected peaks. Upload it next to the recording and the frontend
draws the two on one axis.
"""

from typing import Annotated

import numpy as np
import xarray as xr
from scipy.signal import find_peaks

from arkitekt import App, Description, Task, run
from elektro import Elektro, elektro_service
from elektro.specs import SingleChannelTrace, carried_axes

app = App("detect-spikes", "0.1.0")
app.service(elektro_service)


@app.action
def detect_spikes(
    trace: Annotated[SingleChannelTrace, Description("The recording to search")],
    threshold: Annotated[float, Description("Peaks above this count, in mV")] = -20.0,
    refractory_samples: Annotated[int, Description("Minimum spacing, in samples")] = 20,
    *,
    elektro: Elektro,
    task: Task,
) -> SingleChannelTrace:
    """Finds threshold crossings and stores them as a trace of the same length.
    """
    source = trace.data
    values = np.asarray(source).squeeze()
    task.progress(30, f"Searching {values.size} samples")

    peaks, _ = find_peaks(values, height=threshold, distance=refractory_samples)
    marks = np.zeros_like(values, dtype="float32")
    marks[peaks] = 1.0
    task.progress(70, f"Found {peaks.size} spikes")

    result = elektro.create_array_dataset(
        data=xr.DataArray(marks.reshape(source.shape), dims=source.dims),
        scales=[],
        name=f"spikes (>{threshold} mV)",
        axes=carried_axes(trace, source.dims),
    )
    return result.lens()


if __name__ == "__main__":
    run(app)
