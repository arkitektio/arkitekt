import asyncio
import sys
import time
import logging
from rich.console import Console
from watchdog.observers import Observer
from watchdog.events import (
    FileModifiedEvent,
    FileSystemEventHandler,
    LoggingEventHandler,
)
import os
import subprocess
import janus
import threading
import os
import signal


class QueueHandler(FileSystemEventHandler):
    def __init__(self, *args, sync_q=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.queue = sync_q

    def on_any_event(self, event):
        self.queue.put(event)
        self.queue.join()


def watcher(path, queue, event):
    event_handler = QueueHandler(sync_q=queue)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    while True:
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
        await asyncio.sleep(1)
        yield buffer[len(buffer) - 1]
        buffer = [None]


async def _read_stream(stream, cb):
    while True:
        line = await stream.readline()
        if line:
            cb(line.decode())
        else:
            break


async def run_subproc(cmd, outcb=print, errorcb=print, env=None):

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        await asyncio.wait(
            [_read_stream(proc.stdout, outcb), _read_stream(proc.stderr, errorcb)]
        )
        await proc.wait()
        print("Program Failed. Please Correct Error!")
        return

    except asyncio.CancelledError as e:
        proc.kill()
        proc.terminate()
        await proc.wait()
        raise e


class Host:
    def __init__(
        self,
        path=None,
        run_py="run.py",
        outcb=sys.stdout.write,
        errorcb=sys.stderr.write,
    ) -> None:
        self.script_path = os.path.join(path, run_py)
        self.interpreter_path = sys.executable
        self.process_task = None
        self.console = Console()
        self.outcb = self.console.print
        self.errorcb = self.console.print
        self.env = os.environ.copy()
        self.env["PYTHONUNBUFFERED"] = "1"
        self.env["ARKITEKT_AGENT_DEBUG"] = "True"

    async def restart(self):
        loop = asyncio.get_event_loop()
        if self.process_task:
            print("Cancelling our Initial Task")
            self.process_task.cancel()
            try:
                await self.process_task
            except asyncio.CancelledError as e:
                print("Process Completely Cancelled")

        print("Starting new Task")
        self.process_task = loop.create_task(
            run_subproc(
                [self.interpreter_path, self.script_path],
                outcb=self.outcb,
                errorcb=self.errorcb,
                env=self.env,
            )
        )

    async def run(self, queue):
        await self.restart()

        async for event in buffered_queue(queue, timeout=1):
            if event:
                await self.restart()


async def watch_directory_and_restart(path="watch", run_py="run.py"):

    cancel_event = threading.Event()
    jqueue = janus.Queue()
    loop = asyncio.get_running_loop()
    fut = loop.run_in_executor(None, watcher, path, jqueue.sync_q, cancel_event)

    host = Host(path=path, run_py=run_py)
    await host.run(jqueue.async_q)
    await fut

    jqueue.close()
    await jqueue.wait_closed()
