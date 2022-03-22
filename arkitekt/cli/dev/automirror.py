import asyncio
import os
import sys
import threading
import time
from importlib import import_module, reload

import janus
from arkitekt.api.schema import adefine
from arkitekt.definition.registry import get_current_definition_registry
from rich.console import Console
from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer


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
        os.environ["ARKITEKT_AGENT_DEBUG"] = "True"

    async def reprovide(self):
        registry = get_current_definition_registry()
        registry.reset()
        reload(self.module)

        try:
            if registry.has_definitions():
                for definition, _, _ in registry.definedNodes:
                    await adefine(definition)
        except Exception as e:
            self.console.print_exception()

        self.console.print("Updated :)")

    async def restart(self):
        loop = asyncio.get_event_loop()

        if self.provide_task:
            self.console.print("Files changed, cancelling all tasks")
            self.provide_task.cancel()
            try:
                await self.provide_task
            except asyncio.CancelledError as e:
                self.console.print("Cancelled")

        self.console.print("Running anew..")
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
                    await self.restart()
        except asyncio.CancelledError as e:
            cancel_event.set()
            await fut

        jqueue.close()
        await jqueue.wait_closed()


async def watch_directory_and_mirror(path="watch", entrypoint="run"):
    host = Host(path=path)
    await host.run()
