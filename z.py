from arkitekt import use
from mikro.api.schema import from_xarray
import numpy as np

stream = use("stream_analyze_images")

image = from_xarray(np.zeros((10, 10, 3)))

for table in stream(image):
    print(table)
