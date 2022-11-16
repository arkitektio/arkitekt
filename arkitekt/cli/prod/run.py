from importlib import import_module
import logging
import sys
import os
from arkitekt.apps.fakts import ArkitektFakts
from fakts import Fakts
from fakts.grants.remote.claimprivate import ClaimPrivateGrant
from fakts.discovery.static import StaticDiscovery
from rich.console import Console
from arkitekt import Arkitekt

logger = logging.getLogger(__name__)


class Run:
    def __init__(
        self,
        path=None,
        entrypoint="run",
    ) -> None:

        self.console = Console()
        if path == ".":
            self.watch_path = os.getcwd()
            sys.path.insert(0, self.watch_path)
        else:
            self.watch_path = os.path.join(os.getcwd(), path)

        self.console.print(f"watch_path: {self.watch_path}")

        self.module_path = f"{path}.{entrypoint}" if path != "." else f"{entrypoint}"
        self.module = import_module(self.module_path)
        os.environ["ARKITEKT_AGENT_DEBUG"] = "False"

    async def run(self):

        app = Arkitekt(
            fakts=ArkitektFakts(
                grant=ClaimPrivateGrant(
                    discovery=StaticDiscovery(base_url=os.getenv("FAKTS_ENDPOINT_URL")),
                    client_id=os.getenv("FAKTS_CLIENT_ID"),
                    client_secret=os.getenv("FAKTS_CLIENT_SECRET"),
                )
            )
        )

        async with app:
            await app.rekuest.run()


async def import_directory_and_start(path="watch", entrypoint="run"):
    host = Run(path=path)
    await host.run()
