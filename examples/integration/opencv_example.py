from enum import Enum

import numpy as np
import xarray as xr
from matplotlib import cm

from arkitekt import easy
from mikro.api.schema import (
    RepresentationFragment,
    RepresentationVariety,
    from_xarray,
)
import cv2


app = easy("clahe_cv2")


class Colormap(Enum):
    VIRIDIS = cm.viridis
    PLASMA = cm.plasma


@app.rekuest.register()
def run_clahe(
    rep: RepresentationFragment,
    clip_limit: int = 2,
    tile_grid_size: int = 8,
) -> RepresentationFragment:
    """Clahe

    Runs CLAHE on a representation

    Args:
        rep (RepresentationFragment): _description_
        clip_limit (float, optional): _description_. Defaults to 2.0.
        tile_grid_size (int, optional): _description_. Defaults to 8.

    Returns:
        RepresentationFragment: _description_
    """

    new_array = xr.DataArray(
        np.zeros(rep.data.shape, dtype=rep.data.dtype), dims=rep.data.dims
    )

    rep.data.sel(c=0, t=0, z=0).data.compute()

    clahe = cv2.createCLAHE(
        clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size)
    )

    for c in range(rep.data.sizes.get("c")):
        for t in range(rep.data.sizes.get("t")):
            for z in range(rep.data.sizes.get("z")):
                new_array[c, t, z, :, :] = clahe.apply(
                    rep.data.sel(c=c, t=t, z=z).data.compute()
                ).astype(rep.data.dtype)

    print(new_array.dtype)

    return from_xarray(
        new_array,
        name="CLAHE of" + rep.name,
        tags=["clahe"],
        origins=[rep],
        variety=RepresentationVariety.VOXEL,
    )


if __name__ == "__main__":
    with app:
        app.rekuest.run()
