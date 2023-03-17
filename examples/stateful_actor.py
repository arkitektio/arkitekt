from enum import Enum
import logging

from matplotlib import cm
from rich.logging import RichHandler
from fakts import Fakts
from fakts.grants.remote.device_code import DeviceCodeGrant
from mikro.api.schema import (
    RepresentationFragment,
    get_random_rep,
)
from arkitekt.apps.connected import Arkitekt
from rekuest.actors.functional import (
    CompletlyThreadedActor,
)
from rekuest.api.schema import ProvisionFragment

logging.basicConfig(level="INFO", handlers=[RichHandler()])

logger = logging.getLogger(__name__)


app = Arkitekt(
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
