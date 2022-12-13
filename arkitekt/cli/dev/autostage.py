from datetime import datetime
from importlib import reload, import_module
import asyncio
import asyncio
import sys
import time
from arkitekt import Arkitekt
from rich.console import Console
from arkitekt.apps.fakts import ArkitektFakts
from fakts import Fakts
from fakts.grants.remote.static import StaticGrant
from fakts.discovery.static import StaticDiscovery
from rich.console import Console
from arkitekt import Arkitekt

try:
    from watchdog.observers import Observer
    from watchdog.events import (
        FileModifiedEvent,
        FileSystemEventHandler,
    )
except ImportError:
    print("Please install watchdog to use this feature")
    sys.exit(1)

try:

    import janus
except ImportError:
    print("Please install janus to use this feature")
    sys.exit(1)

import os
import threading

from rekuest.definition.registry import (
    get_default_definition_registry,
)


class QueueHandler(FileSystemEventHandler):
    def __init__(self, *args, sync_q=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.queue = sync_q

    def on_any_event(self, event):
        self.queue.put(event)
        self.queue.join()


def watcher(path, queue, event: threading.Event):
    event_handler = QueueHandler(sync_q=queue)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    while not event.is_set():
        time.sleep(1)

    print("Cancelled because threading event is set")


async def buffered_queue(queue, timeout=4):
    buffer = [None]

    async def iterator():
        while True:
            nana = await queue.get()
            queue.task_done()
            if isinstance(nana, FileModifiedEvent):
                if nana.src_path.lower().endswith((".py")):
                    buffer.append(nana)

    loop = asyncio.get_event_loop()
    loop.create_task(iterator())
    while True:
        await asyncio.sleep(timeout)
        yield buffer[len(buffer) - 1]
        buffer = [None]


class Host:
    def __init__(
        self,
        path=None,
        entrypoint="run",
        token=None,
        endpoint=None,
    ) -> None:

        if path == ".":
            self.watch_path = os.getcwd()
            sys.path.insert(0, self.watch_path)
        else:
            self.watch_path = os.path.join(os.getcwd(), path)

        self.module_path = f"{path}.{entrypoint}" if path != "." else f"{entrypoint}"
        self.module = import_module(self.module_path)
        self.provide_task = None
        self.console = Console()
        self.token = token
        self.endpoint = endpoint
        os.environ["ARKITEKT_AGENT_DEBUG"] = "True"

    async def reprovide(self, endpoint=None, token=None):
        registry = get_default_definition_registry()
        registry.reset()
        reload(self.module)

        try:
            if registry.has_definitions():
                app = Arkitekt(
                    fakts=ArkitektFakts(
                        grant=StaticGrant(
                            discovery=StaticDiscovery(
                                base_url=self.endpoint
                                or os.getenv("FAKTS_ENDPOINT_URL")
                            ),
                            token=self.token or os.getenv("FAKTS_TOKEN"),
                        )
                    )
                )

                async with app:
                    self.console.print(
                        f"[bold green] --------------- Providing {datetime.now()} ------------- [/bold green]"
                    )
                    await app.rekuest.run()

        except Exception as e:
            self.console.print(
                f"[bold red] --------------- Error in App {datetime.now()} ------------- [/bold red]"
            )
            self.console.print_exception()

        except asyncio.CancelledError as e:
            self.console.print(
                f"[bold yellow] --------------- App Cancelled {datetime.now()} ------------- [/bold yellow]"
            )
            raise e

    async def restart(self):
        loop = asyncio.get_event_loop()

        if self.provide_task:
            self.provide_task.cancel()
            try:
                await self.provide_task
            except asyncio.CancelledError as e:
                pass

        self.provide_task = loop.create_task(self.reprovide())

    async def run(self):
        await self.restart()

        jqueue = janus.Queue()

        cancel_event = threading.Event()
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(
            None, watcher, self.watch_path, jqueue.sync_q, cancel_event
        )

        try:
            async for event in buffered_queue(jqueue.async_q, timeout=1):
                if event:
                    self.console.print(
                        f"[bold yellow] --------------- File Changed {datetime.now()} ------------- [/bold yellow]"
                    )
                    await self.restart()
        except asyncio.CancelledError as e:
            cancel_event.set()
            await fut

        jqueue.close()
        await jqueue.wait_closed()


async def watch_directory_and_stage(path="watch", token=None, endpoint=None):
    host = Host(path=path, token=token, endpoint=endpoint)
    await host.run()
