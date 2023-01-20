from datetime import datetime
from arkitekt import easy
from fakts.fakts import Fakts
from mikro.api.schema import (
    OmeroRepresentationInput,
    PlaneInput,
    RepresentationVariety,
    create_experiment,
    create_feature,
    create_label,
    create_metric,
    create_sample,
    from_xarray,
    InputVector,
    RoiTypeInput,
    create_roi,
    create_stage,
    create_position,
)
import xarray as xr
import numpy as np
import time


def main():

    x = easy("create_multidimensional_data")

    with x:

        l = create_experiment(name="Test dfsdfsd")

        stage = create_stage(name="Stage 1", x=0, y=0, z=0)

        for m in range(2):
            elemental_sample = create_sample(
                name=f"Elemental Sample {m}", experiments=[l], tags=["elemental"]
            )

            for i in range(2):
                position = create_position(stage=stage, x=i, y=i, z=i)

                g = from_xarray(
                    xr.DataArray(
                        np.random.randint(0, 255, size=(100, 100, 2)),
                        dims=("x", "y", "c"),
                    ),
                    omero=OmeroRepresentationInput(
                        acquisitionDate=datetime.now(),
                        planes=[
                            PlaneInput(z=i, exposureTime=657.2),
                            PlaneInput(z=i + 1, exposureTime=456.2),
                        ],
                        position=position,
                    ),
                    sample=elemental_sample,
                    variety=RepresentationVariety.VOXEL,
                )

        for m in range(3):

            s = create_sample(name=f"Bad Sample {m}", experiments=[l], tags=["bad"])

            for i in range(3):
                position = create_position(stage=stage, x=i, y=i, z=i)
                g = from_xarray(
                    xr.DataArray(
                        np.random.randint(0, 255, size=(100, 100, 3)),
                        dims=("x", "y", "c"),
                    ),
                    omero=OmeroRepresentationInput(
                        acquisitionDate=datetime.now(),
                        planes=[
                            PlaneInput(z=i, exposureTime=657.2),
                            PlaneInput(z=i + 1, exposureTime=456.2),
                        ],
                    ),
                    sample=s,
                    variety=RepresentationVariety.VOXEL,
                )

                create_metric(key="Increasing", representation=g, value=i)
                create_metric(key="Decreasing", representation=g, value=10 - i)

                t = from_xarray(
                    xr.DataArray(
                        np.random.randint(0, 3, size=(100, 100, 3)),
                        dims=("x", "y", "c"),
                    ),
                    omero=OmeroRepresentationInput(
                        acquisitionDate=datetime.now(),
                        planes=[
                            PlaneInput(z=i, exposureTime=657.2),
                            PlaneInput(z=i + 1, exposureTime=456.2),
                        ],
                    ),
                    sample=s,
                    variety=RepresentationVariety.MASK,
                )
                for x in range(3):
                    theL = create_label(instance=x, representation=g)
                    create_feature(theL, key="Area", value=0.5 * x)
                    create_feature(theL, key="Type", value="Cell")

        print(l.id)


if __name__ == "__main__":

    main()
