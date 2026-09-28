"""Static cases for an app written against ``from arkitekt import ...`` alone.

Checked by basedpyright, not run. A line ending in ``# expect-error`` must be
reported; every other line must not. Every name comes from ``arkitekt``: if an app
had to import the definition space (arkitekt-spec) to write this, that is the bug.
"""

from collections.abc import AsyncGenerator, Generator
from typing import Annotated, Any, assert_type

from arkitekt import (
    App,
    AssignmentHook,
    CallTarget,
    CancelOnDisconnect,
    Default,
    Description,
    LogLevel,
    NoCallerError,
    PortGroupInput,
    Task,
    WrappedFunction,
    model_field,
)


class Config:
    gain: float = 1.0


app = App("cases", "0.1.0", app_context=Config)


@app.state
class Counter:
    count: int = 0


@app.model
class Point:
    x: float = model_field(description="x")


@app.action
def add(a: Annotated[int, Description("first")], b: Annotated[int, Default(2)], task: Task) -> int:
    """Adds, reporting as it goes."""
    task.log("adding", LogLevel.INFO)
    task.progress(50, "half")
    task.pausepoint()
    assert_type(task.id, str)
    assert_type(task.token, str | None)
    return a + b


wrapped: WrappedFunction[..., int] = add


@app.action(policy=CancelOnDisconnect(grace=5.0), port_groups=[PortGroupInput(key="g", ports=("n",))])
def stream(n: int, task: Task) -> Generator[int, None, None]:
    """Streams."""
    yield from range(n)


@app.action
async def astream(n: int, task: Task) -> AsyncGenerator[int, None]:
    """Streams, asynchronously."""
    await task.alog("start")
    await task.aprogress(10)
    await task.apausepoint()
    for i in range(n):
        yield i


@app.action
async def orchestrate(x: int, target: Any, task: Task) -> int:
    """Calls another action as a child of this task."""
    first = await task.acall(target, x, reference="once")
    for value in task.iterate(target, x):
        print(value)
    async for value in task.aiterate(target, x, cancel_timeout=2.0):
        print(value)
    try:
        return int(task.call(target, first))
    except NoCallerError:
        return 0


def takes_a_target(target: CallTarget) -> None: ...


async def on_pause(message: object) -> None: ...


@app.action
def with_hooks(counter: Counter, config: Config, p: Point, task: Task) -> float:
    """Reads state and the app context, and installs a pause hook."""
    task.install_hook(AssignmentHook(id="h", kind="pause", hook=on_pause))
    counter.count += 1
    return p.x * config.gain


Point(x=1.0)
Point(y=1.0)  # expect-error
Counter(count=2)
Counter(count="two")  # expect-error


@app.model
class Measurement:
    """A model without defaults: every field is a constructor parameter."""

    count: int
    area: float


class Stage:
    x: float = 0.0


app.state(Stage, name="stage", required_locks=["stage"])
Measurement(count=1, area=2.0)
Measurement(count=1)  # expect-error


local = Task.local(id="script")
assert_type(add(1, 2, local), int)
local.log("hello")
local.call()  # expect-error
local.progress("half")  # expect-error
