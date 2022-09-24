import xarray as xr
import numpy as np
from mikro.api.schema import (
    OmeroRepresentationInput,
    from_xarray,
    PhysicalSizeInput,
    create_sample,
)
from arkitekt.apps.connected import ConnectedApp


with ConnectedApp() as c:

    x = xr.DataArray(np.zeros((1000, 100, 2, 4, 1)), dims=list("xyzct"))

    size = PhysicalSizeInput(x=35.2, y=323.2)
    omero = OmeroRepresentationInput(physicalSize=size)

    sample = create_sample("test")

    from_xarray(xarray=x, omero=omero, name="johannes", sample=sample)
