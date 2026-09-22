# /// script
# requires-python = ">=3.11"
# dependencies = ["arkitekt[elektro]>=3", "numpy>=1.26"]
# ///
"""Calling: an electrophysiology trace into elektro.

Run:  uv run --script examples/upload_trace.py

elektro is mikro's sibling for signals: the same array datasets, ordered by a
time axis. Two things live somewhere other than where one first looks for them:

- the **unit** of the values is on a coordinate anchor, not on the axis;
- the **sampling rate** is not on the dataset at all. It belongs to a session —
  the clock the recording was made against — so several datasets can share one.

The trace here is a synthetic one second of membrane potential at 20 kHz.
"""

import numpy as np
from kanne.scalars import Duration, Frequency, Unit

from arkitekt import easy
from elektro import elektro_service
from elektro.api.schema import CoordinateAnchorInput, SamplingInput, ValueUnitInput

RATE_HZ = 20_000.0
SECONDS = 1.0


def synthesise() -> np.ndarray:
    """One second of resting potential with a few spikes on top."""
    rng = np.random.default_rng(7)
    n = int(RATE_HZ * SECONDS)
    trace = rng.normal(-65.0, 0.4, n).astype("float32")
    for onset in rng.choice(n - 40, size=12, replace=False):
        shape = np.array([-60, -30, 20, 35, 10, -70, -75, -70], dtype="float32")
        trace[onset : onset + shape.size] = shape
    return trace


def main() -> None:
    """Upload the trace, then give it the clock it was recorded against."""
    trace = synthesise()

    with easy("trace-upload", elektro_service) as elektro:
        folder = elektro.create_folder(name="examples")

        dataset = elektro.create_array_dataset(
            data=trace,
            scales=[],
            name="V soma",
            axes=["t"],
            folder=folder.id,
            anchors=[
                CoordinateAnchorInput(
                    axis_anchors=[],
                    value_unit=ValueUnitInput(unit=Unit("millivolt")),
                )
            ],
        )

        session = elektro.create_session(
            name="example recording",
            datasets=[dataset.id],
            time_unit=Unit("millisecond"),
            sampling=SamplingInput(
                rate=Frequency(f"{RATE_HZ} Hz"), t_start=Duration("0 ms")
            ),
        )
        print(f"uploaded {dataset.id} in session {session.id}")


if __name__ == "__main__":
    main()
