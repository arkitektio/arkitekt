import enum
from fakts.fakts import Fakts
from mikro.api.schema import (
    RepresentationVarietyInput,
    from_xarray,
    create_label,
    create_feature,
)
from arkitekt import easy
import xarray as xr
import numpy as np
from skimage.draw import random_shapes

app = easy("com.example.random_shapes", url="http://localhost:8000/f/")

random_shape_data, labels = random_shapes(
    (300, 300),
    max_shapes=60,
    min_shapes=60,
    channel_axis=None,
    intensity_range=((0, 60)),
)
print(random_shape_data.shape, labels)
print(random_shape_data)
print(random_shape_data)


with app:
    x = from_xarray(
        xr.DataArray(data=random_shape_data, dims=list("xy")),
        name="ioinoinsffff",
        variety=RepresentationVarietyInput.MASK,
    )

    for i, label in enumerate(labels):
        l = create_label(i, x, name=label[0])
        create_feature(l.id, 6, "size")
    print(x)
