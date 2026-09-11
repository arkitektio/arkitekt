"""
 This example shows how to upload an image to the server
 and how to access it again.

 It requires the following packages:
    arkitekt_next
    mikro
 
 If you are not concerned about installing multiple packages, you can
  install them with:

 `pip install "arktitekt[all]"`

 To run this example, first start the server, e.g with
 `konstruktor` and then run this script with python3.

"""

from arkitekt_next import easy
from mikro_next.api.schema import from_array_like
import xarray as xr
import numpy as np

app = easy("upload_test", url="localhost")
# Create a new app with the name "upload_test", we here use the
# default url "http://localhost:80", adjust this if you are running
# the server on a different port or host ()


data = xr.DataArray(np.random.rand(100, 100), dims=["x", "y"])
# Create random image and convert to xarray
# Mikro will automatically inspect the xarray and its dimensions and convert
# it to a 5D array with the following dimensions: (c, t, z, y, x)


with app:
    # Every app needs to be run in a context manager

    image = from_array_like(
        data,
        name="test",
        tags=["test"],
    )
    # The from_xarray function will upload the xarray to the server
    # and return a mikro Image object, which can be used to access the
    # image on the server

    print(image.id)  # Print the id of the image
    # This is a unique identifier for the image on the server
