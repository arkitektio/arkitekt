# /// script
# requires-python = ">=3.11"
# dependencies = ["arkitekt[rekuest,mikro]>=5", "numpy>=1.26", "scikit-image>=0.24", "xarray>=2024.3.0"]
# ///
"""An analysis app says what its actions do to the world.

Run:  uv run --script examples/recovery/declare_analysis.py

``effects=`` is one ordered scale, the ladder HTTP uses for its methods, with the
real-world step on top:

    NONE < REPEATABLE < UNKNOWN (the default) < IRREVERSIBLE

It is *information*, never a rule: whoever decides about a lost task sees it (a
workflow on ``AgentLost.effects``, a person on a hold or in the UI). The server re-runs
nothing because of it.

What crosses between apps is a mikro structure: the image lives in mikro, and every
app reaches it there.
"""

from typing import Annotated

import numpy as np
import xarray as xr
from mikro import Mikro, mikro_service
from mikro.arkitekt.specs import LabelMask, SingleChannelImage, ensure
from skimage.filters import threshold_otsu
from skimage.measure import label

from arkitekt import App, Description, Effects, run

app = App("segmentation", "0.1.0", services=[mikro_service])


@app.action(effects=Effects.NONE)
def count_cells(image: Annotated[SingleChannelImage, Description("The image to count in")]) -> int:
    """Reads the image and counts the objects in it. Changes nothing, so if its agent
    dies, it is simply run again (AT_LEAST_ONCE) unless the caller says otherwise.
    """
    pixels = np.asarray(image.data)
    return int(label(pixels > threshold_otsu(pixels)).max())


@app.action
def segment(
    mikro: Mikro,
    image: Annotated[SingleChannelImage, Description("The image to segment")],
) -> LabelMask:
    """Stores a new label dataset next to the image. No claim (UNKNOWN), and honestly
    so: a re-run stores a *second* dataset. By default a lost run fails; a caller
    who'd rather clean up a duplicate than lose the run asks for AT_LEAST_ONCE.
    """
    pixels = np.asarray(image.data)
    labels = xr.DataArray(
        label(pixels > threshold_otsu(pixels)).astype(np.uint16), dims=image.data.dims
    )
    result = mikro.create_array_dataset(
        data=labels,
        scales=[],
        name="labels",
        axes=image.carried_axes(labels.dims),
        derived_from=[image.derive_identity(value_relation="TRANSFORMED")],
    )
    return ensure(result.lens(), LabelMask)


if __name__ == "__main__":
    run(app)
