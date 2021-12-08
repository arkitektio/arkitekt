import asyncio
from importlib import import_module, reload
from typing import List
from herre.herre import get_current_herre
from herre.wards.base import WardException
from herre.wards.registry import get_ward_registry
from arkitekt.agents.script import ScriptAgent
import logging
import sys
import os
from rich.console import Console
from arkitekt.actors.registry import get_current_actor_registry, register

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

        registry = get_current_actor_registry()

        if registry.has_actors():
            self.console.print(
                "We found functions that ought to be provide. Starting an Agent"
            )
            agent = ScriptAgent(registry=registry)
            await agent.aprovide()

        else:
            self.console.print(
                f"[red] No Functions in {self.module_path} that we can provide found. Exiting!"
            )


async def import_directory_and_start(path="watch", entrypoint="run"):
    host = Run(path=path)
    await host.run()
