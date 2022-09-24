import enum
from fakts.fakts import Fakts
from mikro.api.schema import (
    RepresentationVarietyInput,
    from_xarray,
    create_label,
    create_size_feature,
)
from arkitekt.apps.connected import ConnectedApp
import xarray as xr
import numpy as np
from skimage.draw import random_shapes
import matplotlib.pyplot as plt

app = ConnectedApp(fakts=Fakts(subapp="basic"))

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
        l = create_label(i, x, creator=1, name=label[0])
        create_size_feature(l.id, 6, creator=1)
    print(x)
