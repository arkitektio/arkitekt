from importlib import import_module
import logging
import sys
import os
from rich.console import Console
from rekuest.definition.registry import get_current_definition_registry

logger = logging.getLogger(__name__)


class Run:
    def __init__(
        self,
        path=None,
        entrypoint="run",
    ) -> None:

        if path == ".":
            self.watch_path = os.getcwd()
            sys.path.insert(0, self.watch_path)
        else:
            self.watch_path = os.path.join(os.getcwd(), path)

        self.module_path = f"{path}.{entrypoint}" if path != "." else f"{entrypoint}"
        self.module = import_module(self.module_path)
        self.console = Console()
        os.environ["ARKITEKT_AGENT_DEBUG"] = "False"

    async def run(self):

        registry = get_current_definition_registry()


async def import_directory_and_start(path="watch", entrypoint="run"):
    host = Run(path=path)
    await host.run()
