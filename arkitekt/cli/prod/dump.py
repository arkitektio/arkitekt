from importlib import import_module
import logging
import sys
import os
from arkitekt.apps.fakts import ArkitektFakts
from fakts import Fakts
from rich.console import Console
from arkitekt import Arkitekt
import yaml
import json

logger = logging.getLogger(__name__)


class Dump:
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

        app = Arkitekt(fakts=ArkitektFakts(fakts_path=f"{self.watch_path}/fakts.yaml"))

        if not os.path.exists(f"{self.watch_path}/.arkitekt"):
            os.mkdir(f"{self.watch_path}/.arkitekt")

        async with app:
            x = json.loads(app.fakts.grant.json())
            with open(f"{self.watch_path}/.arkitekt/config.yaml", "w") as file:
                documents = yaml.dump(x, file)

            x = app.rekuest.definition_registry.dump()
            with open(f"{self.watch_path}/.arkitekt/definitions.yaml", "w") as file:
                documents = yaml.dump(x, file)


async def import_directory_and_dump(path="watch", entrypoint="run"):
    host = Dump(path=path)
    await host.run()
