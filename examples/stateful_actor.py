from enum import Enum
import logging
from typing import Optional

import numpy as np
import tifffile
import xarray as xr
from matplotlib import cm
from PIL import Image
from rich.logging import RichHandler
import math
from fakts import Fakts
from fakts.grants.remote.device_code import DeviceCodeGrant
from mikro.api.schema import (
    OmeroFileFragment,
    OmeroFileType,
    ROIFragment,
    ROIType,
    RepresentationFragment,
    SampleFragment,
    Search_representationQuery,
    Search_sampleQuery,
    ThumbnailFragment,
    aexpand_omerofile,
    aexpand_representation,
    aexpand_sample,
    aexpand_thumbnail,
    create_thumbnail,
    from_xarray,
    get_random_rep,
    get_representation,
)
from rekuest.actors.base import Actor
from arkitekt.apps.connected import ConnectedApp
from rekuest.actors.functional import (
    CompletlyThreadedActor,
    FunctionalFuncActor,
    ThreadedFuncActor,
)
from rekuest.api.schema import ProvisionFragment
from rekuest.messages import Assignation

logging.basicConfig(level="INFO", handlers=[RichHandler()])

logger = logging.getLogger(__name__)


app = ConnectedApp(
    fakts=Fakts(subapp="state", grant=DeviceCodeGrant(name="Thumpi", scopes=["openid"]))
)


class Colormap(Enum):
    VIRIDIS = cm.viridis
    PLASMA = cm.plasma


@app.rekuest.register()
class Johannes(CompletlyThreadedActor):
    def provide(self, provision: ProvisionFragment):
        print("on_provide", provision)

        return None

    def unprovide(self):
        return None

    def assign(self, colormap: Colormap) -> RepresentationFragment:
        """Johannes

        Assign a colormap to the representation

        Args:
            colormap (Colormap): _description_

        Returns:
            RepresentationFragment: The generated image
        """
        return get_random_rep()


with app:
    app.rekuest.run()
