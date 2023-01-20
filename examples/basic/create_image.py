from arkitekt import easy
from mikro.api.schema import from_xarray
import xarray as xr
import numpy as np

x = easy("1.0.0", "arkitekt-example")

with x:
    # You can pass either a numpy array or an xarray DataArray, if you pass a numpy array, 
    # we will automatically try to infer the dimensions from the shape of the array otherwise
    # please use and xarray

    l = from_xarray(xr.DataArray(np.zeros((203, 203, 20)), dims=["x", "y", "z"]))
    l.shape

    # l.data will always be a xr.DataArray object with the shape [c,t,z,y,x]
    array = l.data
