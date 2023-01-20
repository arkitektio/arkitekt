from mikro.api.schema import (
    create_stage,
    create_position,
    create_objective,
    create_instrument,
    from_xarray,
    OmeroRepresentationInput,
    PhysicalSizeInput,
)
import tifffile
import glob
from arkitekt import easy
import re
import datetime
import numpy as np

app = easy("fuckme")
p_t = re.compile(r"data/(.*)_s(\d+)_t(\d+).TIF")


pixel_size = 0.1  # maps pixel to um
image_x = 2048
image_y = 2048


with app:

    instrument = create_instrument(name="SoSPIM2", serial_number="123")

    objective = create_objective(
        serial_number="123", name="Cool and stuff", magnification=10
    )

    a = create_stage(
        name="The best stage ever setphane editions Threehunder",
        tags=["acquisition"],
        physical_size=[1, 1, 1],
    )

    positions = [
        create_position(
            stage=a,
            x=m * 44,
            y=n * 44,
            z=0,
            tags=["exposure"],
        )
        for m in range(5)
        for n in range(5)
    ]

    tif_glob = glob.glob("data/*.TIF")

    for tif in range(25):

        image = np.zeros((440, 440))  # with a 10x objective, this is 44um x 44um

        omero = OmeroRepresentationInput(
            position=positions[tif],
            acquisitionDate=datetime.datetime.now() - datetime.timedelta(minutes=tif),
            physicalSize=objective.calculate_physical(a),
            objective=objective,
            instrument=instrument,
        )

        from_xarray(image, name=tif, omero=omero)
